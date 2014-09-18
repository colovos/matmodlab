SUBROUTINE UMAT(STRESS, STATEV, DDSDDE, SSE, SPD, SCD, RPL, &
     DDSDDT, DRPLDE, DRPLDT, STRAN, DSTRAN, TIME, DTIME, TEMP, DTEMP, &
     PREDEF, DPRED, CMNAME, NDI, NSHR, NTENS, NSTATV, PROPS, NPROPS, &
     COORDS, DROT, PNEWDT, CELENT, DFGRD0, DFGRD1, NOEL, NPT, LAYER, &
     KSPT, KSTEP, KINC)

  IMPLICIT NONE
  REAL(8), PARAMETER :: ZERO=0.E+00_8, ONE=1.E+00_8, TWO=2.E+00_8
  REAL(8), PARAMETER :: THREE=3.E+00_8, SIX=6.E+00_8
  CHARACTER*8, INTENT(IN) :: CMNAME
  INTEGER, INTENT(IN) :: NDI, NSHR, NTENS, NSTATV, NPROPS
  INTEGER, INTENT(IN) :: NOEL, NPT, LAYER, KSPT, KSTEP, KINC
  REAL(8), INTENT(IN) :: SSE, SPD, SCD, RPL, DRPLDT, TIME, DTIME, TEMP, DTEMP
  REAL(8), INTENT(IN) :: PNEWDT, CELENT
  REAL(8), INTENT(INOUT) :: STRESS(NTENS), STATEV(NSTATV), DDSDDE(NTENS, NTENS)
  REAL(8), INTENT(INOUT) :: DDSDDT(NTENS), DRPLDE(NTENS)
  REAL(8), INTENT(IN) :: STRAN(NTENS), DSTRAN(NTENS)
  REAL(8), INTENT(IN) :: PREDEF(1), DPRED(1), PROPS(NPROPS), COORDS(3)
  REAL(8), INTENT(IN) :: DROT(3, 3), DFGRD0(3, 3), DFGRD1(3, 3)

  ! LOCAL ARRAYS
  ! EELAS - ELASTIC STRAINS
  ! ETHERM - THERMAL STRAINS
  ! DTHERM - INCREMENTAL THERMAL STRAINS
  ! DELDSE - CHANGE IN STIFFNESS DUE TO TEMPERATURE CHANGE
  INTEGER :: K1, K2
  REAL(8) :: EELAS(6), ETHERM(6), DTHERM(6), DELDSE(6,6), ENU
  REAL(8) :: FAC0, FAC1, EBULK3, EG, EG0, EG2, EG20, ELAM, ELAM0, EMOD
  CHARACTER*120 :: MSG
  CHARACTER*8 :: CHARV(1)
  INTEGER :: INTV(1)
  REAL(8) :: REALV(1)

  IF (NSTATV /= 12) THEN
     MSG = "EXPECTED 12 STATE VARIABLES, GOT %I"
     INTV(1) = NSTATV
     CALL STDB_ABQERR(-3, MSG, INTV, REALV, CHARV)
  END IF

  ! UMAT FOR ISOTROPIC THERMO-ELASTICITY WITH LINEARLY VARYING
  ! MODULI - CANNOT BE USED FOR PLANE STRESS
  ! PROPS(1) - E(T0)
  ! PROPS(2) - NU(T0)
  ! PROPS(3) - T0
  ! PROPS(4) - E(T1)
  ! PROPS(5) - NU(T1)
  ! PROPS(6) - T1
  ! PROPS(7) - ALPHA
  ! PROPS(8) - T_INITIAL

  ! ELASTIC PROPERTIES AT START OF INCREMENT
  FAC1 = (TEMP - PROPS(3)) / (PROPS(6) - PROPS(3))
  IF (FAC1 .LT. ZERO) FAC1 = ZERO
  IF (FAC1 .GT. ONE) FAC1 = ONE
  FAC0 = ONE - FAC1
  EMOD = FAC0 * PROPS(1) + FAC1 * PROPS(4)
  ENU = FAC0 * PROPS(2) + FAC1 * PROPS(5)
  EBULK3 = EMOD / (ONE - TWO * ENU)
  EG20 = EMOD / (ONE + ENU)
  EG0 = EG20 / TWO
  ELAM0 = (EBULK3 - EG20) / THREE

  ! ELASTIC PROPERTIES AT END OF INCREMENT
  FAC1 = (TEMP + DTEMP - PROPS(3)) / (PROPS(6) - PROPS(3))
  IF (FAC1 .LT. ZERO) FAC1 = ZERO
  IF (FAC1 .GT. ONE) FAC1 = ONE
  FAC0 = ONE - FAC1
  EMOD = FAC0 * PROPS(1) + FAC1 * PROPS(4)
  ENU = FAC0 * PROPS(2) + FAC1 * PROPS(5)
  EBULK3 = EMOD / (ONE - TWO * ENU)
  EG2 = EMOD / (ONE + ENU)
  EG = EG2 / TWO
  ELAM = (EBULK3 - EG2) / THREE

  ! ELASTIC STIFFNESS AT END OF INCREMENT AND STIFFNESS CHANGE
  DO K1 = 1,NDI
     DO K2 = 1,NDI
        DDSDDE(K2,K1) = ELAM
        DELDSE(K2,K1) = ELAM - ELAM0
     END DO
     DDSDDE(K1,K1) = EG2 + ELAM
     DELDSE(K1,K1) = EG2 + ELAM - EG20 - ELAM0
  END DO
  DO K1 = NDI + 1,NTENS
     DDSDDE(K1,K1) = EG
     DELDSE(K1,K1) = EG - EG0
  END DO

  ! CALCULATE THERMAL EXPANSION
  DO K1 = 1,NDI
     ETHERM(K1) = PROPS(7) * (TEMP - PROPS(8))
     DTHERM(K1) = PROPS(7) * DTEMP
  END DO
  DO K1 = NDI + 1,NTENS
     ETHERM(K1) = ZERO
     DTHERM(K1) = ZERO
  END DO

  ! CALCULATE STRESS, ELASTIC STRAIN AND THERMAL STRAIN
  DO K1 = 1, NTENS
     DO K2 = 1, NTENS
        STRESS(K2) = STRESS(K2) + DDSDDE(K2,K1) * (DSTRAN(K1) - DTHERM(K1)) &
                   + DELDSE(K2,K1) * (STRAN(K1) - ETHERM(K1))
     END DO
     ETHERM(K1) = ETHERM(K1) + DTHERM(K1)
     EELAS(K1) = STRAN(K1) + DSTRAN(K1) - ETHERM(K1)
  END DO

  ! STORE ELASTIC AND THERMAL STRAINS IN STATE VARIABLE ARRAY
  DO K1 = 1, NTENS
     STATEV(K1) = EELAS(K1)
     STATEV(K1 + NTENS) = ETHERM(K1)
  END DO
  RETURN
END SUBROUTINE UMAT
