
Fortran User Material Interface
###############################

Overview
========

Procedures ``UMAT``, ``UHYPER``, and ``UANISOHYPER_INV`` are called for user defined materials defining the mechanical, hyperelastic, or anisotropic hyperelastic material responses, respectively.  Regardles of the interface procedure used, a fortran compiler must be available for Matmodlab to compile and link user procedures.

References
==========

* :ref:`Role of Material Model`
* :ref:`defining_a_material`
* :ref:`Conventions`
* :ref:`comm_w_matmodlab`

.. _invoke_user_f:

Invoking User Materials
=======================

User defined materials are invoked using the same
``MaterialPointSimulator.Material`` factory method as other materials, but
with additional required and optional arguments.

Required MaterialPointSimulator.Material Agruments
--------------------------------------------------

* The *model* argument must be set to *user*
* The *parameters* must be a ndarray of model constants (specified in the
  order expected by the model).
* *source_files*, a list of model source files. The source files must exist
  and be readable on the file system.

Optional MaterialPointSimulator.Material Arguments
--------------------------------------------------

* *source_directory*, is a directory containing source files.
* *param_names*, is a list of parameter names in the order expected by the model.
  If given, *parameters* must be given as dict of ``name:value`` pairs as for
  builtin models.
* *depvar*, is the number of state dependent variables required
  for the model. Can also be specified as a list of state dependent variable
  names, specified in the order expected by the model. If given as a list, the
  number of state variables allocated is inferred from its length. Matmodlab
  allocates storage for the *depvar* state dependent variables and
  initializes their values to 0.
* *type*, is a string specifying the type of model.  Must be one of "mechanical" (default), "hyperelastic", or "anisohyper".
* *cmname*, is a string giving is the constitutive model name.
* *order*, is a list of strings specifying the ordering of second-order
  symmetric tensors. The default ordering of symmetric second-order tensor
  components is ``xx, yy, zz, xy, yz, xz``. Can be used to change the ordering
  to be consistent with the assumptions of the material model.

Example
-------

::

   mps = MaterialPointSimulator('user_material')
   parameters = np.array([135e9, 53e9, 200e6])
   mps.Material('user', parameters)


.. note:: Abaqus Users:

   Setting the *model* name to one of "*umat*", "*uhyper*", or
   "*uanisohyper_inv*" is equivalient to *model=*"*user*", with
   *behavior=*"*mechanical*", *behavior=*"*hyperelastic*", or
   *behavior=*"*anisohyperelastic*", respectively.

Compiling Fortran Sources
=========================

Matmodlab compiles and links material model sources using ``f2py``.

User Subroutine Interfaces
==========================

.. toctree::
   :maxdepth: 1

   umat
   uhyper
   uanisohyper_inv
