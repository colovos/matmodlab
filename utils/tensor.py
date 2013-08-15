import numpy as np

NSYMM = 6
NSKEW = 3
NTENS = 9
NVEC = 3
I6 = np.array([1, 1, 1, 0, 0, 0], dtype=np.float64)
Z6 = np.zeros(6)
I9 = np.eye(3).flatten()
I3x3 = np.eye(3)

EPSILON = np.array([[[ 0.,  0.,  0.],
                     [ 0.,  0.,  1.],
                     [ 0., -1.,  0.]],
                    [[ 0.,  0., -1.],
                     [ 0.,  0.,  0.],
                     [ 1.,  0.,  0.]],
                    [[ 0.,  1.,  0.],
                     [-1.,  0.,  0.],
                     [ 0.,  0.,  0.]]])


def trace(a):
    return np.sum(a[:3])


def iso(a):
    return trace(a) / 3. * I6


def dev(a):
    return a - iso(a)


def sym(a):
    """Symmetric part of tensor

    Parameters
    ----------
    a : ndarray (9,)

    Returns
    -------
    syma : ndarray (6,)
        syma = (a + a.T) / 2

    """
    return np.array([a[0], a[4], a[8],
                     (a[1] + a[3]) / 2.,
                     (a[5] + a[7]) / 2.,
                     (a[2] + a[6]) / 2.])

def skew(a):
    """Skew-Symmetric part of tensor

    Parameters
    ----------
    a : ndarray (9,)

    Returns
    -------
    w : ndarray (3,)

    Notes
    -----
    If W is the Skew Symmetric part of a, given by

          W = a - (a + a.T) / 2

    the following vector is returned

          w_0 = -W_12
          w_1 = -W_20
          w_2 = -W_01

    The full skew symmetric tensor can be generated by
               0   -w[2]  w[1]
         W =  w[2]   0   -w[0]
             -w[1]  w[0]   0

    """
    return -np.array([(a[7] - a[5]) / 2.,
                      (a[2] - a[6]) / 2.,
                      (a[3] - a[1]) / 2.])


def asmatrix(a):
    """Convert array to matrix

    Parameters
    ----------
    a : ndarray
        Array of shape (6,) or (9,)

    Returns
    -------
    a : ndarray
        Array dimensioned to (3, 3)

    """
    try:
        return a.reshape((3, 3))
    except ValueError:
        return np.array([[a[0], a[3], a[5]],
                         [a[3], a[1], a[4]],
                         [a[5], a[4], a[2]]])


def asarray(a, symm=True, skew=False):
    """Convert matrix to array

    Parameters
    ----------
    a : ndarray
        Array of shape (3, 3)

    Returns
    -------
    a : ndarray
        Array dimensioned to (6,) for symmetric and (9,) for non-symmetric
        input arrays

    """
    if a.shape == (2, 2):
        b = np.zeros((3, 3))
        b[:2, :2], a = a, b
    if symm:
        return .5 * (a + a.T)[[[0, 1, 2, 0, 1, 0], [0, 1, 2, 1, 2, 2]]]
    if skew:
        return -np.array([
                (a[7] - a[5]) / 2., (a[2] - a[6]) / 2., (a[3] - a[1]) / 2.])
    return np.reshape(a, a.size)


def reduce_map(ij, ncoord, ndof=None):
    """Mapping from higher order tensor space to lower order

    Parameters
    ----------
    ij : tuple
        Indeces in the higher-order tensor space (1, 1)
        ij[0] -> ith index
        ij[1] -> jth index

    Returns
    -------
    I : int
        Index in the lower-order tensor space

    Comments
    --------
    Maps according to:

       2D               3D
    00 -> 0           00 -> 0
    11 -> 1           11 -> 1
                      22 -> 2
    01 -> 2           01 -> 3
                      12 -> 4
                      02 -> 5

    """
    if ndof is None:
        ndof = ncoord
    if ndof != ncoord:
        raise WasatchError("NDOF must equal NCOORD (for now)")

    # sort the indices
    ij = sorted(ij)

    if ij[0] == ij[1]:
        return ij[0]

    if ncoord == 2:
        if any(i > 1 for i in ij):
            raise WasatchError("Bad index for 2D mapping: {0}".format(repr(ij)))
        return 2

    if ij == [0, 1]:
        return 3
    elif ij == [1, 2]:
        return 4
    elif ij == [0, 2]:
        return 5
    raise WasatchError("Bad index for 3D mapping: {0}".format(repr(ij)))

reduce_map_C = """
int reduce_map_C(int i, int j, int ncoord) {
  int ij = 100;
  if (i == j) {ij = i;}
  else if (ncoord == 2) {ij = 2;}
  else {
    if ((i == 0 && j == 1) || (i == 1 && j == 0)) {ij = 3;}
    else if ((i == 1 && j == 2) || (i == 2 && j == 1)) {ij = 4;}
    else if ((i == 0 && j == 2) || (i == 2 && j == 0)) {ij = 5;}
  }
  return ij;
}
"""

def isdiag(a):
    """return True if a is diagonal else False"""
    return np.all(a - np.diag(np.diag(a)) <= np.finfo(np.float).eps)


def dot(a, b, symm=False):
    if a.shape == (NSYMM,) and b.shape == (3,):
        adb = np.array([a[0] * b[0] + a[3] * b[1] + a[5] * b[2],
                        a[3] * b[0] + a[1] * b[1] + a[4] * b[2],
                        a[5] * b[0] + a[4] * b[1] + a[2] * b[2]])

    elif a.shape == (NSYMM,) and b.shape == (NTENS,):
        adb = np.array([[a[0] * b[0] + a[3] * b[3] + a[5] * b[6],
                         a[0] * b[1] + a[3] * b[4] + a[5] * b[7],
                         a[0] * b[2] + a[3] * b[5] + a[5] * b[8]],
                        [a[3] * b[0] + a[1] * b[3] + a[4] * b[6],
                         a[3] * b[1] + a[1] * b[4] + a[4] * b[7],
                         a[3] * b[2] + a[1] * b[5] + a[4] * b[8]],
                        [a[5] * b[0] + a[4] * b[3] + a[2] * b[6],
                         a[5] * b[1] + a[4] * b[4] + a[2] * b[7],
                         a[5] * b[2] + a[4] * b[5] + a[2] * b[8]]])

    elif a.shape == (NSYMM,) and b.shape == (NSYMM,):
        adb = np.array([[a[0] * b[0] + a[3] * b[3] + a[5] * b[5],
                         a[3] * b[1] + a[0] * b[3] + a[5] * b[4],
                         a[5] * b[2] + a[3] * b[4] + a[0] * b[5]],
                        [a[3] * b[0] + a[1] * b[3] + a[4] * b[5],
                         a[1] * b[1] + a[3] * b[3] + a[4] * b[4],
                         a[4] * b[2] + a[1] * b[4] + a[3] * b[5]],
                        [a[5] * b[0] + a[4] * b[3] + a[2] * b[5],
                         a[4] * b[1] + a[5] * b[3] + a[2] * b[4],
                         a[2] * b[2] + a[4] * b[4] + a[5] * b[5]]])

    elif a.shape == (NTENS,) and b.shape == (NTENS,):
        adb = np.array([[a[0] * b[0] + a[1] * b[3] + a[2] * b[6],
                         a[0] * b[1] + a[1] * b[4] + a[2] * b[7],
                         a[0] * b[2] + a[1] * b[5] + a[2] * b[8]],
                        [a[3] * b[0] + a[4] * b[3] + a[5] * b[6],
                         a[3] * b[1] + a[4] * b[4] + a[5] * b[7],
                         a[3] * b[2] + a[4] * b[5] + a[5] * b[8]],
                        [a[6] * b[0] + a[7] * b[3] + a[8] * b[6],
                         a[6] * b[1] + a[7] * b[4] + a[8] * b[7],
                         a[6] * b[2] + a[7] * b[5] + a[8] * b[8]]])

    elif a.shape == (NTENS,) and b.shape == (NSYMM,):
        adb = np.array([[a[0] * b[0] + a[1] * b[3] + a[2] * b[5],
                         a[1] * b[1] + a[0] * b[3] + a[2] * b[4],
                         a[2] * b[2] + a[1] * b[4] + a[0] * b[5]],
                        [a[3] * b[0] + a[4] * b[3] + a[5] * b[5],
                         a[4] * b[1] + a[3] * b[3] + a[5] * b[4],
                         a[5] * b[2] + a[4] * b[4] + a[3] * b[5]],
                        [a[6] * b[0] + a[7] * b[3] + a[8] * b[5],
                         a[7] * b[1] + a[6] * b[3] + a[8] * b[4],
                         a[8] * b[2] + a[7] * b[4] + a[6] * b[5]]])
    return asarray(adb, symm=False)

def inv(a):
    """Specialized inverse for 3x3

    Paramters
    ---------
    a : ndarray (3,3)

    Returns
    -------
    ainv : ndarray (3,3)
        Inverse of a

    """
    if a.shape == (3, 3):
        dnom = (-a[2] * a[4] * a[6] + a[1] * a[5] * a[6]
                +a[2] * a[3] * a[7] - a[0] * a[5] * a[7]
                -a[1] * a[3] * a[8] + a[0] * a[4] * a[8])
        return np.array([[-a[5] * a[7] + a[4] * a[8],
                           a[2] * a[7] - a[1] * a[8],
                          -a[2] * a[4] + a[1] * a[5]],
                         [ a[5] * a[6] - a[3] * a[8],
                          -a[2] * a[6] + a[0] * a[8],
                           a[2] * a[3] - a[0] * a[5]],
                         [-a[4] * a[6] + a[3] * a[7],
                           a[1] * a[6] - a[0] * a[7],
                          -a[1] * a[3] + a[0] * a[4]]]) / dnom

    elif a.shape == (2, 2):
        dnom = a[0] * a[3] - a[1] * a[2]
        return np.array([[a[3], a[1]], [a[2], a[0]]]) / dnom

    elif a.shape == (NSYMM,):
        dnom = (a[2] * a[3] ** 2 +
                a[0] * (-a[1] * a[2] + a[4] ** 2) +
                a[5] * (-2. * a[3] * a[4] + a[1] * a[5]))
        return np.array([a[4] ** 2 - a[1] * a[2],
                         a[5] ** 2 - a[0] * a[2],
                         a[3] ** 2 - a[0] * a[1],
                         a[2] * a[3] - a[3] * a[5],
                         a[0] * a[4] - a[3] * a[5],
                         a[1] * a[5] - a[3] * a[4]]) / dnom


def rotate(a, R):
    """Apply a rotation to a second-order symmetric tensor

    Parameters
    ----------
    a : ndarray (6,)
        Second-order tensor stored as 6x1 array
    R : ndarray (6,)
        Second-order rotation tensor stored as 9x1 array

    Returns
    -------
    A = R^T . a . R

    """

    return np.array(
        (a[0] * R[0] ** 2 + a[1] * R[3] ** 2 + a[2] * R[6] ** 2 +
         2. * (a[3] * R[0] * R[3] + a[5] * R[0] * R[6] + a[4] * R[3] * R[6])),
        #
        (a[0] * R[1] ** 2 + a[1] * R[4] ** 2 + a[2] * R[7] ** 2 +
         2. * (a[3] * R[1] * R[4] + a[5] * R[1] * R[7] + a[4] * R[4] * R[7])),
        #
        (a[0] * R[2] ** 2 + a[1] * R[5] ** 2 + a[2] * R[8] ** 2 +
         2. * (a[3] * R[2] * R[5] + a[5] * R[2] * R[8] + a[4] * R[5] * R[8])),
        #
        (a[0] * R[0] * R[1] + a[3] * R[1] * R[3] + a[3] * R[0] * R[4] +
         a[1] * R[3] * R[4] + a[5] * R[1] * R[6] + a[4] * R[4] * R[6] +
         a[5] * R[0] * R[7] + a[4] * R[3] * R[7] + a[2] * R[6] * R[7]),
        #
        (a[0] * R[1] * R[2] + a[3] * R[2] * R[4] + a[3] * R[1] * R[5] +
         a[1] * R[4] * R[5] + a[5] * R[2] * R[7] + a[4] * R[5] * R[7] +
         a[5] * R[1] * R[8] + a[4] * R[4] * R[8] + a[2] * R[7] * R[8]),
        #
        (a[0] * R[0] * R[2] + a[3] * R[2] * R[3] + a[3] * R[0] * R[5] +
         a[1] * R[3] * R[5] + a[5] * R[2] * R[6] + a[4] * R[5] * R[6] +
         a[5] * R[0] * R[8] + a[4] * R[3] * R[8] + a[2] * R[6] * R[8]))


def axialv(a):
    """Construct the axial vector associated with a

    w_i = -1/2 e_ijk a_jk

    Parameters
    ----------
    a : ndarray (3, 3)
        Second-order tensors

    Returns
    -------
    w : ndarray (3,)
        Axial vector associated with a


    """
    return .5 * np.array([a[2, 1] - a[1, 2],
                          a[0, 2] - a[2, 0],
                          a[1, 0] - a[0, 1]])

def axialt(a):
    """Construct the axial tensor associated with a

    W_ij = e_ijk a_k

    Parameters
    ----------
    a : ndarray (3,)
        Vector

    Returns
    W : ndarray (3,)
        Axial tensor associated with a

    """
    return np.array([[  0, -a[2], a[1]],
                     [a[2],   0, -a[0]],
                    [-a[1], a[0],   0]])


def u2e(Uij, kappa):
    """Compute the Seth-Hill generalized strain from the stretch U

    Parameters
    ----------
    Uij : ndarray
        Stretch, stored as 1d array of length 6

    kappa : float
        The Seth-Hill parameter

    Notes
    -----
    The Seth-Hill strain is defined
            strain = (1/kappa)*[(stretch)^kappa - 1]
    and
            stretch = displacement + 1

    In the limit as kappa->0, the Seth-Hill strain becomes

            strain = ln(stretch).

    """
    eij = np.zeros(6)
    if kappa != 0:
        eij[:3] = 1. / kappa * (Uij[:3] ** kappa - 1.)
    else:
        eij[:3] = np.log(Uij[:3])
    return eij
