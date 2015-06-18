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

   \Tensor{v}{}{}{} = \{v_x, v_y, v_z\}

Tensor Storage
==============

In general, second-order symmetric tensors are stored as 6x1 arrays with the
following ordering

.. math::
   :label: order-symtens

   \AA = \{A_{xx}, A_{yy}, A_{zz}, A_{xy}, A_{yz}, A_{xz}\}

Tensor components are used for all second-order symmetric tensors.

Nonsymmetric, second-order tensors are stored as 9x1 arrays in row major
ordering, i.e.,

.. math::

   \BB = \{A_{xx}, A_{xy}, A_{xz},
           A_{yx}, A_{yy}, A_{yz},
           A_{zx}, A_{zy}, A_{zz}\}

.. note::

   The tensor order is runtime configurable using *ordering* keyword to the ``MaterialModel`` constructor.  See :ref:`invoke_user_f` for details.


Engineering Strains
===================

The shear components of strain-like tensors are sent to the material model as
engineering strains, i.e.

.. math::

   \Strain = \{\epsilon_{xx}, \epsilon_{yy}, \epsilon_{zz}, 2\epsilon_{xy}, 2\epsilon_{xz}, 2\epsilon_{yz}\}
           = \{\epsilon_{xx}, \epsilon_{yy}, \epsilon_{zz}, \gamma_{xy}, \gamma_{xz}, \gamma_{yz}\}

matmodlab Namespace
===================

Input scripts to Matmodlab should include::

   from matmodlab import *

to populate the script's namespace with Matmodlab specific parameters and methods.

Parameters
----------

Some useful parameters exposed by importing ``matmodlab`` are

* ``ROOT_D``, The root ``matmodlab`` directory
* ``PKG_D``, The ``matmodlab/lib`` directory, the location shared objects are copied
* ``MAT_D``, The directory where builtin materials are contained

Methods
-------

Some useful methods exposed by importing ``matmodlab`` are

* ``MaterialPointSimulator``, The material point simulator constructor
* ``Permutator``, The permutator constructor
* ``Optimizer``, The optimizer constructor

Each of these methods is described in more detail in the following sections.
