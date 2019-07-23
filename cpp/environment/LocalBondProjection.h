// Copyright (c) 2010-2019 The Regents of the University of Michigan
// This file is part of the freud project, released under the BSD 3-Clause License.

#ifndef LOCAL_BOND_PROJECTION_H
#define LOCAL_BOND_PROJECTION_H

#include <complex>
#include <memory>
#include <tbb/tbb.h>

#include "Box.h"
#include "NeighborList.h"
#include "VectorMath.h"

/*! \file LocalBondProjection.h
    \brief Compute the projection of nearest neighbor bonds for each particle onto some
    set of reference vectors, defined in the particles' local reference frame.
*/

namespace freud { namespace environment {

//! Project the local bond onto all symmetrically equivalent vectors to proj_vec.
//! Return the maximal projection value.
float computeMaxProjection(const vec3<float> proj_vec, const vec3<float> local_bond,
                           const quat<float>* equiv_qs, unsigned int Nequiv);

class LocalBondProjection
{
public:
    //! Constructor
    LocalBondProjection();

    //! Destructor
    ~LocalBondProjection();

    //! Compute the maximal local bond projection
    void compute(box::Box& box, 
        const vec3<float>* proj_vecs,  unsigned int n_proj,
        const vec3<float>* points, const quat<float>* orientations, unsigned int m_n_points,
        const vec3<float>* query_points, unsigned int n_query_points,
        const quat<float>* equiv_quats, unsigned int n_equiv,
        const freud::locality::NeighborList* nlist);

    //! Get a reference to the last computed maximal local bond projection array
    std::shared_ptr<float> getProjections()
    {
        return m_local_bond_proj;
    }

    //! Get a reference to the last computed normalized maximal local bond projection array
    std::shared_ptr<float> getNormedProjections()
    {
        return m_local_bond_proj_norm;
    }

    unsigned int getNQueryPoints()
    {
        return m_n_query_points;
    }

    unsigned int getNPoints()
    {
        return m_n_points;
    }

    unsigned int getNproj()
    {
        return m_n_proj;
    }

    const box::Box& getBox() const
    {
        return m_box;
    }

private:
    box::Box m_box;               //!< Last used simulation box
    unsigned int m_n_query_points;            //!< Last number of particles computed
    unsigned int m_n_points;          //!< Last number of reference particles used for computation
    unsigned int m_n_proj;         //!< Last number of projection vectors used for computation
    unsigned int m_n_equiv;        //!< Last number of equivalent reference orientations used for computation
    unsigned int m_tot_num_neigh; //!< Last number of total bonds used for computation

    std::shared_ptr<float> m_local_bond_proj;      //!< Local bond projection array computed
    std::shared_ptr<float> m_local_bond_proj_norm; //!< Normalized local bond projection array computed
};

}; }; // end namespace freud::environment

#endif // LOCAL_BOND_PROJECTION_H
