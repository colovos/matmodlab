.. _Conventions:

Matmodlab Conventions
#####################

Overview
========

Conventions used throught Matmodlab are described

Dimension
=========

Material models are always called with full 3D tensors.

Vector Storage
==============

Vector components are stored as

.. math::

   v_i = \{v_x, v_y, v_z\}

Tensor Storage
==============

In general, second-order symmetric tensors are stored as 6x1 arrays with the
following ordering

.. math::
   :label: order-symtens

   A_{ij} = \{A_{xx}, A_{yy}, A_{zz}, A_{xy}, A_{yz}, A_{xz}\}

Tensor components are used for all second-order symmetric tensors.

Nonsymmetric, second-order tensors are stored as 9x1 arrays in row major
ordering, i.e.,

.. math::

   B_{ij} = \{B_{xx}, B_{xy}, B_{xz},
              B_{yx}, B_{yy}, B_{yz},
              B_{zx}, B_{zy}, B_{zz}\}

.. note::

   The tensor order is runtime configurable using *ordering* keyword to the ``MaterialModel`` constructor.  See :ref:`invoke_user_f` for details.


Engineering Strains
===================

The shear components of strain-like tensors are sent to the material model as
engineering strains, i.e.

.. math::

   \epsilon_{ij} = \{\epsilon_{xx}, \epsilon_{yy}, \epsilon_{zz}, 2\epsilon_{xy}, 2\epsilon_{xz}, 2\epsilon_{yz}\}
           = \{\epsilon_{xx}, \epsilon_{yy}, \epsilon_{zz}, \gamma_{xy}, \gamma_{xz}, \gamma_{yz}\}

matmodlab Namespace
===================

Input scripts to Matmodlab should include::

   from matmodlab import *

to populate the script's namespace with Matmodlab specific parameters and methods.

Parameters
----------

Some useful parameters exposed by importing ``matmodlab`` are

* ``ROOT_D``, the root ``matmodlab`` directory
* ``PKG_D``, the ``matmodlab/lib`` directory, the location shared objects are copied
* ``MAT_D``, the directory where builtin materials are contained

Methods
-------

Some useful methods exposed by importing ``matmodlab`` are

* ``MaterialPointSimulator``, the material point simulator constructor
* ``Permutator``, the permutator constructor
* ``Optimizer``, the optimizer constructor

Each of these methods is described in more detail in the following sections.

Symbolic Constants
------------------

The following symbolic constants are exposed by importing ``matmodlab``:

* ``XX, YY, ZZ, XY, YZ, XZ``, constants representing the *xx*, *yy*, *zz*, *xy*, *yz*, and *xz* components of second-order symmetric tensors.
* ``MECHANICAL``, ``HYPERELASTIC``, ``ANISOHYPER`` are constants representing user defined materials for mechanical, hyperelastic, and anisotropic-hyperelastic material behaviors (see :ref:`user_mats`).
* ``WLF`` specifies a WLF time-temperature shift (see :ref:`trs`)
* ``PRONY`` specifies a prony series input to the viscoelastic model (see :ref:`viscoelastic`)
* ``ISOTROPIC`` specifies isotropic thermal expansion (see :ref:`expansion`)
* ``USER`` specifies that a user developed mode is of type "user"
* ``UMAT`` specifies that a user developed mode is of type "umat"
* ``UHYPER`` specifies that a user developed mode is of type "uhyper"
* ``UANISOHYPER_INV`` specifies that a user developed mode is of type "uanisohyper_inv"
