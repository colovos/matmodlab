from math import sin, cos
from utils.constants import TOOR3, ROOT3
from utils.elas import compute_elastic_constants, NAME_MAP

# Elastic constants
EC_LAME = 0
EC_SHEAR = 1
EC_YOUNGS = 2
EC_NU = 3 # Poisson's ratio
EC_BULK = 4
EC_CONSTRAINED = 5
EC_SIGRATIO = 6 # SIGy/SIGx in uniaxial strain = nu/(1-nu)
EC_C10 = 7
EC_C01 = 8
EC_D1 = 9

# Wave speeds
WS_LONGITUDINAL = 7 # longitudinal wave speed = sqrt(H/rho)
WS_TRANSVERSE = 8  # shear (TRANSVERSE) wave speed = sqrt(G/rho)
WS_BULK = 9 # bulk/plastic wave speed = sqrt(K/rho)=SQRT(cl^2-4(ct^2)/3)
WS_THINROD = 10 # thin rod elastic wave speed  = sqrt(E/rho)

DENSITY = 11

# Strengths
Y_SHEAR = 30
Y_TENSION = 31

# Hardening
HARD_MOD = 32
HARD_PARAM = 33

# Drucker-Prager parameters: Sqrt[J2] = A + B I1
DP_A = 50
DP_B = 51

# Cohesion and friction angle
COHESION = 61
FRICTION_ANGLE = 62

TEMP0 = 80


class Completion:
    def __init__(self, dict):
        self.__dict__.update(dict)
    def __getitem__(self, key):
        return self.__dict__.get(key)
    def __str__(self):
        x = ",".join("{0}".format(v) for (k,v) in self.__dict__.items()
                     if isinstance(k, int))
        return "PropertyCompletion[{0}]".format(x)


def complete_properties(parameters, propmap):
    """Complete the material properties

    Parameters
    ----------
    parameters : ndarray
        Array of material parameters
    propmap : dict
        Mapping of property to parameter

    """
    if not propmap:
        return

    # check if any hyperelastic parameters are given and, if so, compute
    # equivalent linear elastic parameters
    if EC_C10 in propmap:
        c10 = parameters[propmap.index(EC_C10)]
        if EC_C01 in propmap:
            c01 = parameters[propmap.index(EC_C01)]
        else:
            c01 = 0.
        g = 2. * (c10 + c01)
        propmap.append(EC_SHEAR)
        parameters = np.append(parameters, g)

        if EC_D1 in propmap:
            k = 2. / parameters[propmap.index(EC_D1)]
            propmap.append(EC_BULK)
            parameters = np.append(parameters, k)

    completion = {}
    elas = [None] * 12
    for (i, idx) in enumerate(propmap):
        completion[i] = None
        if idx < 12:
            elas[idx] = parameters[i]
    completion.update(compute_elastic_constants(elas, disp=1))

    # complete inelastic properties
    ys = completion.get(Y_SHEAR)
    yt = completion.get(Y_TENSION)
    if ys is not None:
        if yt is None:
            yt = ys / TOOR3
    elif yt is not None:
        if ys is None:
            ys = yt * TOOR3
    completion[Y_SHEAR] = ys
    completion[Y_TENSION] = yt

    A = completion.get(DP_A)
    B = completion.get(DP_B)
    C = completion.get(COHESION)
    phi = completion.get(FRICTION_ANGLE)
    if phi is None and B is not None:
        # B = 2 Sin[PHI] / ROOT3 / (3 + Sin[PHI])
        x = 0.
        for i in range(25):
            f = B - 2. * sin(x) * TOOR3 / (3. + sin(x))
            df = (2. * ROOT3 * cos(x) / (3. * (sin(x) + 3.)) -
                  2. * ROOT3 * sin(x) * cos(x)/(3. * (sin(x) + 3.) ** 2))
            dx = -f / df
            x += dx
            if dx < 1.E-08:
                phi = x
                break
        else:
            logger.warn("unable to determine friction angle")

    if C is None and A is not None and phi is not None:
        C = A * ROOT3 * (3. - sin(phi)) / 6. / cos(phi)

    # by this point, A, B, C, phi are known - if there is enough info to
    # compute them. If there is not, compute A based on yield in shear
    if A is None:
        A = ys

    completion[DP_A] = A
    completion[DP_B] = B
    completion[COHESION] = C
    completion[FRICTION_ANGLE] = phi

    return Completion(completion)
