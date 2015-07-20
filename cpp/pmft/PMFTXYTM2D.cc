#include "PMFTXYTM2D.h"
#include "ScopedGILRelease.h"

#include <stdexcept>
#ifdef __SSE2__
#include <emmintrin.h>
#endif

#ifdef ENABLE_OPENMP
#include <omp.h>
#endif

#include "VectorMath.h"

using namespace std;
using namespace boost::python;

using namespace tbb;

/*! \file PMFTXYTM2D.cc
    \brief Routines for computing radial density functions
*/

namespace freud { namespace pmft {

PMFTXYTM2D::PMFTXYTM2D(float max_x, float max_y, float max_T, unsigned int nbins_x, unsigned int nbins_y, unsigned int nbins_T)
    : m_box(trajectory::Box()), m_max_x(max_x), m_max_y(max_y),
      m_nbins_x(nbins_x), m_nbins_y(nbins_y), m_nbins_T(nbins_T)
    {
    if (nbins_x < 1)
        throw invalid_argument("must be at least 1 bin in x");
    if (nbins_y < 1)
        throw invalid_argument("must be at least 1 bin in y");
    if (nbins_T < 1)
        throw invalid_argument("must be at least 1 bin in T");
    if (max_x < 0.0f)
        throw invalid_argument("max_x must be positive");
    if (max_y < 0.0f)
        throw invalid_argument("max_y must be positive");
    if (max_T < 0.0f)
        throw invalid_argument("max_T must be positive");

    // calculate dx, dy, dT
    m_dx = 2.0 * m_max_x / float(m_nbins_x);
    m_dy = 2.0 * m_max_y / float(m_nbins_y);
    m_dT = 2.0 * m_max_T / float(m_nbins_T);

    if (m_dx > max_x)
        throw invalid_argument("max_x must be greater than dx");
    if (m_dy > max_y)
        throw invalid_argument("max_y must be greater than dy");
    if (m_dT > max_T)
        throw invalid_argument("max_T must be greater than dT");

    // precompute the bin center positions for x
    m_x_array = boost::shared_array<float>(new float[m_nbins_x]);
    for (unsigned int i = 0; i < m_nbins_x; i++)
        {
        float x = float(i) * m_dx;
        float nextx = float(i+1) * m_dx;
        m_x_array[i] = -m_max_x + ((x + nextx) / 2.0);
        }

    // precompute the bin center positions for y
    m_y_array = boost::shared_array<float>(new float[m_nbins_y]);
    for (unsigned int i = 0; i < m_nbins_y; i++)
        {
        float y = float(i) * m_dy;
        float nexty = float(i+1) * m_dy;
        m_y_array[i] = -m_max_y + ((y + nexty) / 2.0);
        }

    // precompute the bin center positions for T
    m_T_array = boost::shared_array<float>(new float[m_nbins_T]);
    for (unsigned int i = 0; i < m_nbins_T; i++)
        {
        float T = float(i) * m_dT;
        float nextT = float(i+1) * m_dT;
        m_T_array[i] = -m_max_T + ((T + nextT) / 2.0);
        }

    // create and populate the pcf_array
    m_pcf_array = boost::shared_array<unsigned int>(new unsigned int[m_nbins_T * m_nbins_y * m_nbins_x]);
    memset((void*)m_pcf_array.get(), 0, sizeof(unsigned int)*m_nbins_T * m_nbins_y * m_nbins_x);

    m_lc = new locality::LinkCell(m_box, sqrtf(m_max_x*m_max_x + m_max_y*m_max_y));
    }

PMFTXYTM2D::~PMFTXYTM2D()
    {
    for (tbb::enumerable_thread_specific<unsigned int *>::iterator i = m_local_pcf_array.begin(); i != m_local_pcf_array.end(); ++i)
        {
        delete[] (*i);
        }
    delete m_lc;
    }

class CombinePCFXYTM2D
    {
    private:
        unsigned int m_nbins_x;
        unsigned int m_nbins_y;
        unsigned int m_nbins_T;
        unsigned int *m_pcf_array;
        tbb::enumerable_thread_specific<unsigned int *>& m_local_pcf_array;
    public:
        CombinePCFXYTM2D(unsigned int nbins_x,
                         unsigned int nbins_y,
                         unsigned int nbins_T,
                         unsigned int *pcf_array,
                         tbb::enumerable_thread_specific<unsigned int *>& local_pcf_array)
            : m_nbins_x(nbins_x), m_nbins_y(nbins_y), m_nbins_T(nbins_T), m_pcf_array(pcf_array), m_local_pcf_array(local_pcf_array)
        {
        }
        void operator()( const blocked_range<size_t> &myBin ) const
            {
            Index3D b_i = Index3D(m_nbins_x, m_nbins_y, m_nbins_T);
            for (size_t i = myBin.begin(); i != myBin.end(); i++)
                {
                for (size_t j = 0; j < m_nbins_y; j++)
                    {
                    for (size_t k = 0; k < m_nbins_y; k++)
                        {
                        for (tbb::enumerable_thread_specific<unsigned int *>::const_iterator local_bins = m_local_pcf_array.begin();
                             local_bins != m_local_pcf_array.end(); ++local_bins)
                            {
                            m_pcf_array[b_i((int)i, (int)j, (int)k)] += (*local_bins)[b_i((int)i, (int)j, (int)k)];
                            }
                        }
                    }
                }
            }
    };

class ComputePMFTXYTM2D
    {
    private:
        tbb::enumerable_thread_specific<unsigned int *>& m_pcf_array;
        unsigned int m_nbins_x;
        unsigned int m_nbins_y;
        unsigned int m_nbins_T;
        const trajectory::Box m_box;
        const float m_max_x;
        const float m_max_y;
        const float m_max_T;
        const float m_dx;
        const float m_dy;
        const float m_dT;
        const locality::LinkCell *m_lc;
        vec3<float> *m_ref_points;
        float *m_ref_orientations;
        const unsigned int m_Nref;
        vec3<float> *m_points;
        float *m_orientations;
        const unsigned int m_Np;
    public:
        ComputePMFTXYTM2D(tbb::enumerable_thread_specific<unsigned int *>& pcf_array,
                          unsigned int nbins_x,
                          unsigned int nbins_y,
                          unsigned int nbins_T,
                          const trajectory::Box &box,
                          const float max_x,
                          const float max_y,
                          const float max_T,
                          const float dx,
                          const float dy,
                          const float dT,
                          const locality::LinkCell *lc,
                          vec3<float> *ref_points,
                          float *ref_orientations,
                          unsigned int Nref,
                          vec3<float> *points,
                          float *orientations,
                          unsigned int Np)
            : m_pcf_array(pcf_array), m_nbins_x(nbins_x), m_nbins_y(nbins_y), m_nbins_T(nbins_T), m_box(box),
              m_max_x(max_x), m_max_y(max_y), m_max_T(max_T), m_dx(dx), m_dy(dy), m_dT(dT), m_lc(lc),
              m_ref_points(ref_points), m_ref_orientations(ref_orientations), m_Nref(Nref), m_points(points),
              m_orientations(orientations), m_Np(Np)
        {
        }
        void operator()( const blocked_range<size_t> &myR ) const
            {
            assert(m_ref_points);
            assert(m_points);
            assert(m_Nref > 0);
            assert(m_Np > 0);

            float dx_inv = 1.0f / m_dx;
            float maxxsq = m_max_x * m_max_x;
            float dy_inv = 1.0f / m_dy;
            float maxysq = m_max_y * m_max_y;
            float dT_inv = 1.0f / m_dT;

            Index3D b_i = Index3D(m_nbins_x, m_nbins_y, m_nbins_T);

            bool exists;
            m_pcf_array.local(exists);
            if (! exists)
                {
                m_pcf_array.local() = new unsigned int [m_nbins_x*m_nbins_y*m_nbins_T];
                memset((void*)m_pcf_array.local(), 0, sizeof(unsigned int)*m_nbins_x*m_nbins_y*m_nbins_T);
                }

            // for each reference point
            for (size_t i = myR.begin(); i != myR.end(); i++)
                {
                // get the cell the point is in
                vec3<float> ref = m_ref_points[i];
                unsigned int ref_cell = m_lc->getCell(ref);

                // loop over all neighboring cells
                const std::vector<unsigned int>& neigh_cells = m_lc->getCellNeighbors(ref_cell);
                for (unsigned int neigh_idx = 0; neigh_idx < neigh_cells.size(); neigh_idx++)
                    {
                    unsigned int neigh_cell = neigh_cells[neigh_idx];

                    // iterate over the particles in that cell
                    locality::LinkCell::iteratorcell it = m_lc->itercell(neigh_cell);
                    for (unsigned int j = it.next(); !it.atEnd(); j=it.next())
                        {
                        vec3<float> delta = m_box.wrap(m_points[j] - ref);
                        float rsq = dot(delta, delta);

                        if (rsq < 1e-6)
                            {
                            continue;
                            }
                        // rotate interparticle vector
                        vec2<float> myVec(delta.x, delta.y);
                        rotmat2<float> myMat = rotmat2<float>::fromAngle(-m_ref_orientations[i]);
                        vec2<float> rotVec = myMat * myVec;
                        float x = rotVec.x + m_max_x;
                        float y = rotVec.y + m_max_y;
                        // calculate angles
                        float dTheta1 = atan2(delta.y, delta.x);
                        float dTheta2 = atan2(-delta.y, -delta.x);
                        float T1 = dTheta1 - m_ref_orientations[i];
                        float T2 = dTheta2 - m_orientations[j];
                        float T = T1 - T2 + m_max_T;

                        // bin that point
                        float binx = floorf(x * dx_inv);
                        float biny = floorf(y * dy_inv);
                        float binT = floorf(T * dT_inv);
                        // fast float to int conversion with truncation
                        #ifdef __SSE2__
                        unsigned int ibinx = _mm_cvtt_ss2si(_mm_load_ss(&binx));
                        unsigned int ibiny = _mm_cvtt_ss2si(_mm_load_ss(&biny));
                        unsigned int ibinT = _mm_cvtt_ss2si(_mm_load_ss(&binT));
                        #else
                        unsigned int ibinx = (unsigned int)(binx);
                        unsigned int ibiny = (unsigned int)(biny);
                        unsigned int ibinT = (unsigned int)(binT);
                        #endif

                        if ((ibinx < m_nbins_x) && (ibiny < m_nbins_y) && (ibinT < m_nbins_T))
                            {
                            ++m_pcf_array.local()[b_i(ibinx, ibiny, ibinT)];
                            }
                        }
                    }
                } // done looping over reference points
            }
    };

//! \internal
//! helper function to reduce the thread specific arrays into the boost array
void PMFTXYTM2D::reducePCF()
    {
    memset((void*)m_pcf_array.get(), 0, sizeof(unsigned int)*m_nbins_x*m_nbins_y*m_nbins_T);
    parallel_for(blocked_range<size_t>(0,m_nbins_x),
                 CombinePCFXYTM2D(m_nbins_x,
                                  m_nbins_y,
                                  m_nbins_T,
                                  m_pcf_array.get(),
                                  m_local_pcf_array));
    }

//! Get a reference to the PCF array
boost::shared_array<unsigned int> PMFTXYTM2D::getPCF()
    {
    reducePCF();
    return m_pcf_array;
    }

//! Get a reference to the PCF array
boost::python::numeric::array PMFTXYTM2D::getPCFPy()
    {
    reducePCF();
    unsigned int *arr = m_pcf_array.get();
    std::vector<intp> dims(3);
    dims[0] = m_nbins_T;
    dims[1] = m_nbins_y;
    dims[2] = m_nbins_x;
    return num_util::makeNum(arr, dims);
    }

//! \internal
/*! \brief Function to reset the pcf array if needed e.g. calculating between new particle types
*/
void PMFTXYTM2D::resetPCF()
    {
    for (tbb::enumerable_thread_specific<unsigned int *>::iterator i = m_local_pcf_array.begin(); i != m_local_pcf_array.end(); ++i)
        {
        memset((void*)(*i), 0, sizeof(unsigned int)*m_nbins_x*m_nbins_y*m_nbins_T);
        }
    // memset((void*)m_pcf_array.get(), 0, sizeof(unsigned int)*m_nbins_x*m_nbins_y*m_nbins_T);
    }

//! \internal
/*! \brief Helper function to direct the calculation to the correct helper class
*/
void PMFTXYTM2D::accumulate(vec3<float> *ref_points,
                         float *ref_orientations,
                         unsigned int Nref,
                         vec3<float> *points,
                         float *orientations,
                         unsigned int Np)
    {
    m_lc->computeCellList(m_box, points, Np);
    parallel_for(blocked_range<size_t>(0,Nref),
                 ComputePMFTXYTM2D(m_local_pcf_array,
                                   m_nbins_x,
                                   m_nbins_y,
                                   m_nbins_T,
                                   m_box,
                                   m_max_x,
                                   m_max_y,
                                   m_max_T,
                                   m_dx,
                                   m_dy,
                                   m_dT,
                                   m_lc,
                                   ref_points,
                                   ref_orientations,
                                   Nref,
                                   points,
                                   orientations,
                                   Np));
    }

void PMFTXYTM2D::accumulatePy(trajectory::Box& box,
                              boost::python::numeric::array ref_points,
                              boost::python::numeric::array ref_orientations,
                              boost::python::numeric::array points,
                              boost::python::numeric::array orientations)
    {
    // validate input type and rank
    m_box = box;
    num_util::check_type(ref_points, NPY_FLOAT);
    num_util::check_rank(ref_points, 2);
    num_util::check_type(ref_orientations, NPY_FLOAT);
    num_util::check_rank(ref_orientations, 1);
    num_util::check_type(points, NPY_FLOAT);
    num_util::check_rank(points, 2);
    num_util::check_type(orientations, NPY_FLOAT);
    num_util::check_rank(orientations, 1);

    // validate that the 2nd dimension is only 3
    num_util::check_dim(points, 1, 3);
    unsigned int Np = num_util::shape(points)[0];

    num_util::check_dim(ref_points, 1, 3);
    unsigned int Nref = num_util::shape(ref_points)[0];

    // check the size of angles to be correct
    num_util::check_dim(ref_orientations, 0, Nref);
    num_util::check_dim(orientations, 0, Np);

    // get the raw data pointers and compute the cell list
    vec3<float>* ref_points_raw = (vec3<float>*) num_util::data(ref_points);
    float* ref_orientations_raw = (float*) num_util::data(ref_orientations);
    vec3<float>* points_raw = (vec3<float>*) num_util::data(points);
    float* orientations_raw = (float*) num_util::data(orientations);

        // compute with the GIL released
        {
        util::ScopedGILRelease gil;
        accumulate(ref_points_raw,
                   ref_orientations_raw,
                   Nref,
                   points_raw,
                   orientations_raw,
                   Np);
        }
    }

void export_PMFTXYTM2D()
    {
    class_<PMFTXYTM2D>("PMFTXYTM2D", init<float, float, float, float, float, float>())
        .def("getBox", &PMFTXYTM2D::getBox, return_internal_reference<>())
        .def("accumulate", &PMFTXYTM2D::accumulatePy)
        .def("getPCF", &PMFTXYTM2D::getPCFPy)
        .def("resetPCF", &PMFTXYTM2D::resetPCFPy)
        .def("getX", &PMFTXYTM2D::getXPy)
        .def("getY", &PMFTXYTM2D::getYPy)
        .def("getT", &PMFTXYTM2D::getTPy)
        ;
    }

}; }; // end namespace freud::pmft
