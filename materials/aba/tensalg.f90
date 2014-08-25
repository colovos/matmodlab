! *************************************************************************** !
! TENSOR ALGEBRA PACKAGE
!
! NOTES
! -----
! 1) THIS FILE MUST BE LINKED AGAINST LAPACK. FOR TESTING, USE
!    blas_lapack-lite.f. WHEN USED IN ABAQUS, LAPACK IS PROVIDED. BUT, LAPACK
!    IS ONLY USED FOR THE EXPM AND SQRTM PROCEDURES. IF THOSE TWO PROCEDURES
!    ARE NOT NEEDED, LAPACK DEPENDENCY IS REMOVED.
! 2) FOR EXPM, THIS FILE MUST ALSO BE LINKED AGAINST dgpadm.f
! 3) PROCEDURE MAKES EXPLICIT CALL TO ABAQUS STDB_ABQERR FOR ERROR HANDLING.
!    FOR USE OUTSIDE OF ABAQUS, REPLACE CALL TO STDB_ABQERR WITH APPROPRIATE
!    PRINT AND STOP STATEMENTS.
! 4) VOIGHT FORM OF SYMMETRIC TENSOR STORAGE FOLLOWS ABAQUS STANDARD:
!
!                        [XX YY ZZ XY YZ XZ]
!
!    AND NON-SYMMETRIC SECOND ORDER TENSORS ARE STORED AS
!
!                             [XX XY XZ]
!                             [YX YY YZ]
!                             [ZX ZY ZZ]
!
! 5) FOR SPEED, MANY PROCEDURES (MATRIX INVERSION, DETERMINANT, ETC.) ARE HARD
!    CODED WITH THE STORAGE LISTED ABOVE IMPLIED. PROCEDURES THUSLY HARD CODED
!    HAD CODE AUTO GENERATED BY SYMPY TO ASSURE ACCURACY. SEE THE
!    Expressions.ipynb NOTEBOOK IN THE nb DIRECTORY.
! *************************************************************************** !
MODULE TENSALG
  USE NUMBERS
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: DET, INV, DBD, DEV, ISO, SQRTM, MAG, ASARRAY, ASMAT, EYE, EXPM, DOT
  PUBLIC :: TRACE, I6, INVSHUF, DYAD, PUSH, PULL, IDSPLIT, INVARS

  ! ********************************************** PARAMETER DECLARATIONS *** !
  REAL(KIND=DP), PARAMETER :: VOIGHT(6)=(/ONE,ONE,ONE,TWO,TWO,TWO/)
  REAL(KIND=DP), PARAMETER :: I6(6)=(/ONE,ONE,ONE,ZERO,ZERO,ZERO/)
  REAL(KIND=DP), PARAMETER :: I3x3(3,3)=RESHAPE((/ ONE, ZERO, ZERO,&
                                                   ZERO, ONE, ZERO,&
                                                   ZERO, ZERO, ONE/), (/3,3/))

  ! *************************************************** PUBLIC INTERFACES *** !
  ! PUBLIC INTERFACES
  INTERFACE DET
     MODULE PROCEDURE DET_3X3, DET_6X1
  END INTERFACE DET
  INTERFACE DBD
     MODULE PROCEDURE DBD_3X3, DBD_6X1
  END INTERFACE DBD
  INTERFACE INV
     MODULE PROCEDURE INV_3X3, INV_6X1
  END INTERFACE INV
  INTERFACE MAG
     MODULE PROCEDURE MAG_3X3, MAG_6X1
  END INTERFACE MAG
  INTERFACE IDSPLIT
     MODULE PROCEDURE IDSPLIT_3X3, IDSPLIT_6X1
  END INTERFACE IDSPLIT
  INTERFACE DEV
     MODULE PROCEDURE DEV_3X3, DEV_6X1
  END INTERFACE DEV
  INTERFACE ISO
     MODULE PROCEDURE ISO_3X3, ISO_6X1
  END INTERFACE ISO
  INTERFACE SQRTM
     MODULE PROCEDURE SQRTM_3X3, SQRTM_6X1
  END INTERFACE SQRTM
  INTERFACE EXPM
     MODULE PROCEDURE EXPM_3X3, EXPM_6X1
  END INTERFACE EXPM
  INTERFACE DOT
     MODULE PROCEDURE D_LA_RA, D_LM_RM, D_LA_RM, D_LM_RA
  END INTERFACE DOT
  INTERFACE TRACE
     MODULE PROCEDURE TR_3X3, TR_6X1
  END INTERFACE TRACE
  INTERFACE PUSH
     MODULE PROCEDURE PUSH_6X6, PUSH_6X1
  END INTERFACE PUSH
  INTERFACE PULL
     MODULE PROCEDURE PULL_6X1
  END INTERFACE PULL
  INTERFACE INVARS
     MODULE PROCEDURE INVARS_6X1
  END INTERFACE INVARS

! ***************************************************** MODULE PROCEDURES *** !
CONTAINS

  FUNCTION EYE(N)
    ! ----------------------------------------------------------------------- !
    ! NxN IDENTITY TENSOR
    ! ----------------------------------------------------------------------- !
    INTEGER, INTENT(IN) :: N
    REAL(KIND=DP) :: EYE(N,N)
    INTEGER :: I
    EYE = ZERO
    FORALL(I=1:N) EYE(I,I) = ONE
  END FUNCTION EYE

  ! ************************************************************************* !

  REAL(KIND=DP) FUNCTION DET_3X3(A)
    ! ----------------------------------------------------------------------- !
    ! DETERMINANT OF SECOND ORDER TENSOR STORED AS 3x3
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP), INTENT(IN) :: A(3,3)
    DET_3X3 = A(1,1) * A(2,2) * A(3,3) - A(1,2) * A(2,1) * A(3,3) &
            + A(1,2) * A(2,3) * A(3,1) + A(1,3) * A(3,2) * A(2,1) &
            - A(1,3) * A(3,1) * A(2,2) - A(2,3) * A(3,2) * A(1,1)
  END FUNCTION DET_3X3

  REAL(KIND=DP) FUNCTION DET_6X1(A)
    ! ----------------------------------------------------------------------- !
    ! DETERMINANT OF SECOND ORDER TENSOR STORED AS 6X1 ARRAY
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP), INTENT(IN) :: A(6)
    DET_6X1 = A(1) * A(2) * A(3) - A(1) * A(6) ** 2 &
            - A(2) * A(5) ** 2 - A(3) * A(4) ** 2 &
            + TWO * A(4) * A(5) * A(6)
  END FUNCTION DET_6X1

  ! ************************************************************************* !

  FUNCTION INV_6X1(A)
    ! ----------------------------------------------------------------------- !
    ! INVERSE OF 3X3 SYMMETRIC TENSOR STORED AS 6X1 ARRAY
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP) :: INV_6X1(6)
    REAL(KIND=DP), INTENT(IN) :: A(6)
    INV_6X1(1) = A(2) * A(3) - A(6) ** 2
    INV_6X1(2) = A(1) * A(3) - A(5) ** 2
    INV_6X1(3) = A(1) * A(2) - A(4) ** 2
    INV_6X1(4) = -A(3) * A(4) + A(5) * A(6)
    INV_6X1(5) = -A(2) * A(5) + A(4) * A(6)
    INV_6X1(6) = -A(1) * A(6) + A(4) * A(5)
    INV_6X1 = INV_6X1 / DET_6X1(A)
  END FUNCTION INV_6X1

  FUNCTION INV_3X3(A)
    ! ----------------------------------------------------------------------- !
    ! INVERSE OF SYMMETRIC SECOND ORDER TENSOR STORED AS 3X3 MATRIX
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP) :: INV_3X3(3,3)
    REAL(KIND=DP), INTENT(IN) :: A(3,3)
    INV_3X3(1,1) =  A(2,2) * A(3,3) - A(2,3) * A(3,2)
    INV_3X3(1,2) = -A(1,2) * A(3,3) + A(1,3) * A(3,2)
    INV_3X3(1,3) =  A(1,2) * A(2,3) - A(1,3) * A(2,2)
    INV_3X3(2,1) = -A(2,1) * A(3,3) + A(2,3) * A(3,1)
    INV_3X3(2,2) =  A(1,1) * A(3,3) - A(1,3) * A(3,1)
    INV_3X3(2,3) = -A(1,1) * A(2,3) + A(1,3) * A(2,1)
    INV_3X3(3,1) =  A(2,1) * A(3,2) - A(2,2) * A(3,1)
    INV_3X3(3,2) = -A(1,1) * A(3,2) + A(1,2) * A(3,1)
    INV_3X3(3,3) =  A(1,1) * A(2,2) - A(1,2) * A(2,1)
    INV_3X3 = INV_3X3 / DET_3X3(A)
  END FUNCTION INV_3X3

  ! ************************************************************************* !

  REAL(KIND=DP) FUNCTION MAG_6X1(A)
    ! ----------------------------------------------------------------------- !
    ! L2-NORM (EUCLIDEAN MAGNITUDE) OF SECOND ORDER TENSOR STORED AS 6X1 ARRAY
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP), INTENT(IN) :: A(6)
    MAG_6X1 = SQRT(DBD_6X1(A, A))
    RETURN
  END FUNCTION MAG_6X1

  REAL(KIND=DP) FUNCTION MAG_3X3(A)
    ! ----------------------------------------------------------------------- !
    ! L2-NORM (EUCLIDEAN MAGNITUDE) OF SECOND ORDER TENSOR STORED AS 6X1 ARRAY
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP), INTENT(IN) :: A(3,3)
    MAG_3X3 = SQRT(DBD_3X3(A, A))
    RETURN
  END FUNCTION MAG_3X3

  ! ************************************************************************* !

  REAL(KIND=DP) FUNCTION DBD_6X1(A, B)
    ! ----------------------------------------------------------------------- !
    ! DOUBLE DOT OF SECOND ORDER TENSORS STORED AS 6X1 ARRAYS
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP), INTENT(IN) :: A(6), B(6)
    DBD_6X1 = SUM(A * B * VOIGHT)
    RETURN
  END FUNCTION DBD_6X1

  REAL(KIND=DP) FUNCTION DBD_3X3(A, B)
    ! ----------------------------------------------------------------------- !
    ! DOUBLE DOT OF SECOND ORDER TENSORS STORED AS 3X3 ARRAYS
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP), INTENT(IN) :: A(3,3), B(3,3)
    DBD_3X3 = SUM(A * B)
    RETURN
  END FUNCTION DBD_3X3

  ! ************************************************************************* !

  FUNCTION TR_6X1(A)
    ! ----------------------------------------------------------------------- !
    ! TRACE OF SECOND ORDER TENSORS STORED AS 6X1 ARRAYS
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP) :: TR_6X1
    REAL(KIND=DP), INTENT(IN) :: A(6)
    TR_6X1 = SUM(A(1:3))
    RETURN
  END FUNCTION TR_6X1

  FUNCTION TR_3X3(A)
    ! ----------------------------------------------------------------------- !
    ! TRACE OF SECOND ORDER TENSORS STORED AS 3X3 ARRAYS
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP) :: TR_3X3
    REAL(KIND=DP), INTENT(IN) :: A(3,3)
    TR_3X3 = A(1,1) + A(2,2) + A(3,3)
    RETURN
  END FUNCTION TR_3X3

  ! ************************************************************************* !

  FUNCTION ISO_6X1(A, METRIC)
    ! ----------------------------------------------------------------------- !
    ! ISOTROPIC PART OF SECOND ORDER TENSORS STORED AS 6X1 ARRAYS
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP) :: ISO_6X1(6)
    REAL(KIND=DP), INTENT(IN) :: A(6)
    REAL(KIND=DP), INTENT(IN), OPTIONAL :: METRIC(6)
    REAL(KIND=DP) :: I(6), X(6)
    REAL(KIND=DP), PARAMETER :: W(6)=(/ONE,ONE,ONE,TWO,TWO,TWO/)
    IF (PRESENT(METRIC)) THEN
       X = INV_6X1(METRIC)
       I = METRIC
    ELSE
       X = I6
       I = I6
    END IF
    ISO_6X1 = SUM(W * A * I) / THREE * X
    RETURN
  END FUNCTION ISO_6X1

  FUNCTION ISO_3X3(A, METRIC)
    ! ----------------------------------------------------------------------- !
    ! ISOTROPIC PART OF SECOND ORDER TENSORS STORED AS 3X3 ARRAYS
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP) :: ISO_3X3(3,3)
    REAL(KIND=DP), INTENT(IN) :: A(3,3)
    REAL(KIND=DP), INTENT(IN), OPTIONAL :: METRIC(3,3)
    REAL(KIND=DP) :: I(3,3), X(3,3)
    IF (PRESENT(METRIC)) THEN
       X = INV_3X3(METRIC)
       I = METRIC
    ELSE
       X = EYE(3)
       I = EYE(3)
    END IF
    ISO_3X3 = DBD_3X3(A, I) / THREE * X
    RETURN
  END FUNCTION ISO_3X3

  ! ************************************************************************* !

  SUBROUTINE IDSPLIT_6X1(LA, METRIC, ISOA, DEVA)
    ! ----------------------------------------------------------------------- !
    ! ISTROPIC/DEVIATORIC SPLIT OF SECOND ORDER TENSOR STORED AS 6X1 ARRAYS
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP), INTENT(IN) :: LA(6)
    REAL(KIND=DP), INTENT(IN), OPTIONAL :: METRIC(6)
    REAL(KIND=DP), INTENT(OUT) :: ISOA(6), DEVA(6)
    REAL(KIND=DP) :: M(6)
    M = I6
    IF (PRESENT(METRIC)) M = METRIC
    ISOA = ISO_6X1(LA, M)
    DEVA = LA - ISOA
    RETURN
  END SUBROUTINE IDSPLIT_6X1

  SUBROUTINE IDSPLIT_3X3(LM, METRIC, ISOM, DEVM)
    ! ----------------------------------------------------------------------- !
    ! ISTROPIC/DEVIATORIC SPLIT OF SECOND ORDER TENSOR STORED AS 3x3 MATRIX
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP), INTENT(IN) :: LM(3,3)
    REAL(KIND=DP), INTENT(IN), OPTIONAL :: METRIC(3,3)
    REAL(KIND=DP), INTENT(OUT) :: ISOM(3,3), DEVM(3,3)
    REAL(KIND=DP) :: M(3,3)
    M = I3X3
    IF (PRESENT(METRIC)) M = METRIC
    ISOM = ISO_3X3(LM, M)
    DEVM = LM - ISOM
    RETURN
  END SUBROUTINE IDSPLIT_3X3

  ! ************************************************************************* !

  FUNCTION DEV_6X1(LA, METRIC)
    ! ----------------------------------------------------------------------- !
    ! DEVIATORIC PART OF SECOND ORDER TENSORS STORED AS 6X1 ARRAYS
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP) :: DEV_6X1(6)
    REAL(KIND=DP), INTENT(IN) :: LA(6)
    REAL(KIND=DP), INTENT(IN), OPTIONAL :: METRIC(6)
    REAL(KIND=DP) :: M(6)
    M = I6
    IF (PRESENT(METRIC)) M = METRIC
    DEV_6X1 = LA - ISO_6X1(LA, M)
    RETURN
  END FUNCTION DEV_6X1
  FUNCTION DEV_3X3(LM, METRIC)
    ! DEVIATORIC PART OF SECOND ORDER TENSORS STORED AS 3X3 ARRAYS
    REAL(KIND=DP) :: DEV_3X3(3,3)
    REAL(KIND=DP), INTENT(IN) :: LM(3,3)
    REAL(KIND=DP), INTENT(IN), OPTIONAL :: METRIC(3,3)
    REAL(KIND=DP) :: M(3,3)
    M = EYE(3)
    IF (PRESENT(METRIC)) M = METRIC
    DEV_3X3 = LM - ISO_3X3(LM, M)
    RETURN
  END FUNCTION DEV_3X3

  ! ************************************************************************* !

  FUNCTION ASMAT(A)
    ! ----------------------------------------------------------------------- !
    ! CONVERT TENSOR STORED AS 6x1 TO 3x3
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP) :: ASMAT(3,3)
    REAL(KIND=DP), INTENT(IN) :: A(:)
    ASMAT = ZERO
    ASMAT(1,1) = A(1); ASMAT(1,2) = A(4); ASMAT(1,3) = A(5)
    ASMAT(2,1) = A(4); ASMAT(2,2) = A(2); ASMAT(2,3) = A(6)
    ASMAT(3,1) = A(5); ASMAT(3,2) = A(6); ASMAT(3,3) = A(3)
  END FUNCTION ASMAT

  FUNCTION ASARRAY(A)
    ! ----------------------------------------------------------------------- !
    ! CONVERT TENSOR STORED AS 3x3 TO 6x1
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP) :: ASARRAY(6)
    REAL(KIND=DP), INTENT(IN) :: A(3,3)
    ASARRAY = ZERO
    ASARRAY(1) = A(1,1); ASARRAY(4) = A(1,2); ASARRAY(5) = A(1,3)
                         ASARRAY(2) = A(2,2); ASARRAY(6) = A(2,3)
                                              ASARRAY(3) = A(3,3)
  END FUNCTION ASARRAY

  ! ************************************************************************* !

  FUNCTION SYMLEAFF(F)
    ! ----------------------------------------------------------------------- !
    ! COMPUTE A 6X6 MANDEL MATRIX THAT IS THE SYM-LEAF TRANSFORMATION OF THE
    ! INPUT 3X3 MATRIX F.
    ! ----------------------------------------------------------------------- !
    !
    ! INPUT
    ! -----
    !    F: ANY 3X3 MATRIX (IN CONVENTIONAL 3X3 STORAGE)
    !
    ! OUTPUT
    ! ------
    !    FF: 6X6 MANDEL MATRIX FOR THE SYM-LEAF TRANSFORMATION MATRIX
    !
    ! NOTES
    ! -----
    ! IF A IS ANY SYMMETRIC TENSOR, AND IF {A} IS ITS 6X1 MANDEL ARRAY, THEN
    ! THE 6X1 MANDEL ARRAY FOR THE TENSOR B=F.A.TRANSPOSE[F] MAY BE COMPUTED
    ! BY
    !                       {B}=[FF]{A}
    !
    ! IF F IS A DEFORMATION F, THEN B IS THE "PUSH" (SPATIAL) TRANSFORMATION
    ! OF THE REFERENCE TENSOR A IF F IS INVERSE[F], THEN B IS THE "PULL"
    ! (REFERENCE) TRANSFORMATION OF THE SPATIAL TENSOR A, AND THEREFORE B
    ! WOULD BE INVERSE[FF]{A}.
    !
    ! IF F IS A ROTATION, THEN B IS THE ROTATION OF A, AND
    ! FF WOULD BE BE A 6X6 ORTHOGONAL MATRIX, JUST AS IS F
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP), INTENT(IN) :: F(3,3)
    REAL(KIND=DP) :: SYMLEAFF(6,6)
    SYMLEAFF(1,1) = F(1,1) ** 2
    SYMLEAFF(1,2) = F(1,2) ** 2
    SYMLEAFF(1,3) = F(1,3) ** 2
    SYMLEAFF(1,4) = TWO * F(1,1) * F(1,2)
    SYMLEAFF(1,5) = TWO * F(1,1) * F(1,3)
    SYMLEAFF(1,6) = TWO * F(1,2) * F(1,3)
    SYMLEAFF(2,1) = F(2,1) ** 2
    SYMLEAFF(2,2) = F(2,2) ** 2
    SYMLEAFF(2,3) = F(2,3) ** 2
    SYMLEAFF(2,4) = TWO * F(2,1) * F(2,2)
    SYMLEAFF(2,5) = TWO * F(2,1) * F(2,3)
    SYMLEAFF(2,6) = TWO * F(2,2) * F(2,3)
    SYMLEAFF(3,1) = F(3,1) ** 2
    SYMLEAFF(3,2) = F(3,2) ** 2
    SYMLEAFF(3,3) = F(3,3) ** 2
    SYMLEAFF(3,4) = TWO * F(3,1) * F(3,2)
    SYMLEAFF(3,5) = TWO * F(3,1) * F(3,3)
    SYMLEAFF(3,6) = TWO * F(3,2) * F(3,3)
    SYMLEAFF(4,1) = F(1,1) * F(2,1)
    SYMLEAFF(4,2) = F(1,2) * F(2,2)
    SYMLEAFF(4,3) = F(1,3) * F(2,3)
    SYMLEAFF(4,4) = F(1,1) * F(2,2) + F(1,2) * F(2,1)
    SYMLEAFF(4,5) = F(1,1) * F(2,3) + F(1,3) * F(2,1)
    SYMLEAFF(4,6) = F(1,2) * F(2,3) + F(1,3) * F(2,2)
    SYMLEAFF(5,1) = F(1,1) * F(3,1)
    SYMLEAFF(5,2) = F(1,2) * F(3,2)
    SYMLEAFF(5,3) = F(1,3) * F(3,3)
    SYMLEAFF(5,4) = F(1,1) * F(3,2) + F(1,2) * F(3,1)
    SYMLEAFF(5,5) = F(1,1) * F(3,3) + F(1,3) * F(3,1)
    SYMLEAFF(5,6) = F(1,2) * F(3,3) + F(1,3) * F(3,2)
    SYMLEAFF(6,1) = F(2,1) * F(3,1)
    SYMLEAFF(6,2) = F(2,2) * F(3,2)
    SYMLEAFF(6,3) = F(2,3) * F(3,3)
    SYMLEAFF(6,4) = F(2,1) * F(3,2) + F(2,2) * F(3,1)
    SYMLEAFF(6,5) = F(2,1) * F(3,3) + F(2,3) * F(3,1)
    SYMLEAFF(6,6) = F(2,2) * F(3,3) + F(2,3) * F(3,2)
    RETURN
  END FUNCTION SYMLEAFF

  ! ************************************************************************* !

  FUNCTION INVSHUF(A,B)
    REAL(KIND=DP) :: INVSHUF(6,6)
    REAL(KIND=DP), INTENT(IN) :: A(6), B(6)
    REAL(KIND=DP) :: FAC
    FAC = HALF
    INVSHUF(1,1) = A(1) * B(1)
    INVSHUF(1,2) = A(4) * B(4)
    INVSHUF(1,3) = A(5) * B(5)
    INVSHUF(1,4) = FAC * A(1) * B(4)  +  FAC * A(4) * B(1)
    INVSHUF(1,5) = FAC * A(1) * B(5)  +  FAC * A(5) * B(1)
    INVSHUF(1,6) = FAC * A(4) * B(5)  +  FAC * A(5) * B(4)
    INVSHUF(2,1) = A(4) * B(4)
    INVSHUF(2,2) = A(2) * B(2)
    INVSHUF(2,3) = A(6) * B(6)
    INVSHUF(2,4) = FAC * A(2) * B(4)  +  FAC * A(4) * B(2)
    INVSHUF(2,5) = FAC * A(4) * B(6)  +  FAC * A(6) * B(4)
    INVSHUF(2,6) = FAC * A(2) * B(6)  +  FAC * A(6) * B(2)
    INVSHUF(3,1) = A(5) * B(5)
    INVSHUF(3,2) = A(6) * B(6)
    INVSHUF(3,3) = A(3) * B(3)
    INVSHUF(3,4) = FAC * A(5) * B(6)  +  FAC * A(6) * B(5)
    INVSHUF(3,5) = FAC * A(3) * B(5)  +  FAC * A(5) * B(3)
    INVSHUF(3,6) = FAC * A(3) * B(6)  +  FAC * A(6) * B(3)
    INVSHUF(4,1) = A(4) * B(1)
    INVSHUF(4,2) = A(2) * B(4)
    INVSHUF(4,3) = A(6) * B(5)
    INVSHUF(4,4) = FAC * A(2) * B(1)  +  FAC * A(4) * B(4)
    INVSHUF(4,5) = FAC * A(4) * B(5)  +  FAC * A(6) * B(1)
    INVSHUF(4,6) = FAC * A(2) * B(5)  +  FAC * A(6) * B(4)
    INVSHUF(5,1) = A(5) * B(1)
    INVSHUF(5,2) = A(6) * B(4)
    INVSHUF(5,3) = A(3) * B(5)
    INVSHUF(5,4) = FAC * A(5) * B(4)  +  FAC * A(6) * B(1)
    INVSHUF(5,5) = FAC * A(3) * B(1)  +  FAC * A(5) * B(5)
    INVSHUF(5,6) = FAC * A(3) * B(4)  +  FAC * A(6) * B(5)
    INVSHUF(6,1) = A(5) * B(4)
    INVSHUF(6,2) = A(6) * B(2)
    INVSHUF(6,3) = A(3) * B(6)
    INVSHUF(6,4) = FAC * A(5) * B(2)  +  FAC * A(6) * B(4)
    INVSHUF(6,5) = FAC * A(3) * B(4)  +  FAC * A(5) * B(6)
    INVSHUF(6,6) = FAC * A(3) * B(2)  +  FAC * A(6) * B(6)
    RETURN
  END FUNCTION INVSHUF

  ! ************************************************************************* !

  FUNCTION DD66X6(A, X, JOB)
    ! ----------------------------------------------------------------------- !
    ! MULTIPLY A FOURTH-ORDER TENSOR A TIMES A SECOND-ORDER TENSOR B (OR VICE
    ! VERSA IF JOB=-1)
    ! ----------------------------------------------------------------------- !
    !
    ! INPUT
    ! -----
    ! A : NDARRAY (6,6)
    !     MANDEL MATRIX FOR A GENERAL (NOT NECESSARILY MAJOR-SYM) FOURTH-ORDER
    !     MINOR-SYM MATRIX
    ! X : NDARRAY(6,)
    !     VOIGT MATRIX
    !
    ! OUTPUT
    ! ------
    ! A:X IF JOB=1
    ! X:A IF JOB=-1
    INTEGER, INTENT(IN), OPTIONAL :: JOB
    REAL(KIND=DP) :: DD66X6(6)
    REAL(KIND=DP), INTENT(IN) :: X(6), A(6,6)
    INTEGER :: IJ, IO
    REAL(KIND=DP) :: T(6)
    REAL(KIND=DP), PARAMETER :: W(6)=(/ZERO,ZERO,ZERO,ROOT2,ROOT2,ROOT2/)
    ! ------------------------------------------------------------ DD66X6 --- !
    T = X * W
    DD66X6 = ZERO
    IO = 1
    IF (PRESENT(JOB)) IO = JOB
    SELECT CASE(IO)
    CASE(1)
       ! ...COMPUTE THE MANDEL FORM OF A:X
       FORALL(IJ=1:6) DD66X6(IJ) = SUM(A(IJ,:) * T(:))
    CASE(-1)
       ! ...COMPUTE THE MANDEL FORM OF X:A
       FORALL(IJ=1:6) DD66X6(IJ) = SUM(T(:) * A(:, IJ))
    CASE DEFAULT
       PRINT*, 'UNKNOWN JOB SENT TO DD66X6'
       CALL XIT
    END SELECT
    ! ...CONVERT RESULT TO VOIGT FORM
    DD66X6(4:6) = DD66X6(4:6) * TOOR2
    RETURN
  END FUNCTION DD66X6

  ! ************************************************************************* !

  FUNCTION SQRTM_6X1(A)
    ! ----------------------------------------------------------------------- !
    ! COMPUTES THE MATRIX SQRT
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP) :: SQRTM_6X1(6)
    REAL(KIND=DP), INTENT(IN) :: A(6)
    REAL(KIND=DP) :: B(3,3),SQRTB(3,3)
    B = ASMAT(A)
    SQRTB = SQRTM_3X3(B)
    SQRTM_6X1 = ASARRAY(SQRTB)
  END FUNCTION SQRTM_6X1

  FUNCTION SQRTM_3X3(A)
    ! ----------------------------------------------------------------------- !
    ! COMPUTES THE MATRIX SQRT
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP) :: SQRTM_3X3(3,3)
    REAL(KIND=DP), INTENT(IN) :: A(3,3)
    INTEGER, PARAMETER :: N=3, LWORK=3*N-1
    REAL(KIND=DP) :: W(N), WORK(LWORK), V(3,3), L(3,3)
    INTEGER :: INFO
    SQRTM_3X3 = ZERO
    IF (ISDIAG(A)) THEN
       SQRTM_3X3(1,1) = SQRT(A(1,1))
       SQRTM_3X3(2,2) = SQRT(A(2,2))
       SQRTM_3X3(3,3) = SQRT(A(3,3))
       RETURN
    END IF
    ! EIGENVALUES/VECTORS OF A
    V = A
    CALL DSYEV("V", "L", 3, V, 3, W, WORK, LWORK, INFO)
    L = ZERO
    L(1,1) = SQRT(W(1))
    L(2,2) = SQRT(W(2))
    L(3,3) = SQRT(W(3))
    SQRTM_3X3 = MATMUL(MATMUL(V, L ), TRANSPOSE(V))
    RETURN
  END FUNCTION SQRTM_3X3

  ! ************************************************************************* !

  FUNCTION ISDIAG(A)
    ! ----------------------------------------------------------------------- !
    ! IS A DIAGONAL?
    ! ----------------------------------------------------------------------- !
    LOGICAL :: ISDIAG
    REAL(KIND=DP), INTENT(IN) :: A(3,3)
    ISDIAG = ALL(ABS(A - DIAG(A)) <= EPSILON(A))
    RETURN
  END FUNCTION ISDIAG

  ! ************************************************************************* !

  FUNCTION DIAG(A)
    ! ----------------------------------------------------------------------- !
    ! CREATE DIAGONAL 3x3 WITH ENTRIES = A
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP) :: DIAG(3,3)
    REAL(KIND=DP), INTENT(IN) :: A(3,3)
    DIAG = ZERO
    DIAG(1,1) = A(1,1)
    DIAG(2,2) = A(2,2)
    DIAG(3,3) = A(3,3)
    RETURN
  END FUNCTION DIAG

  ! ************************************************************************* !

  FUNCTION EXPM_6X1(A)
    ! ----------------------------------------------------------------------- !
    ! MATRIX EXPONENTIAL
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP) :: EXPM_6X1(6)
    REAL(KIND=DP), INTENT(IN) :: A(6)
    REAL(KIND=DP) :: B(3,3),EXPB(3,3)
    B = ASMAT(A)
    EXPB = EXPM_3X3(B)
    EXPM_6X1 = ASARRAY(EXPB)
  END FUNCTION EXPM_6X1

  FUNCTION EXPM_3X3(A)
    ! ----------------------------------------------------------------------- !
    ! MATRIX EXPONENTIAL
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP) :: EXPM_3X3(3,3)
    REAL(KIND=DP), INTENT(IN) :: A(3,3)
    INTEGER, PARAMETER :: M=3, LDH=3, IDEG=6, LWSP=4*M*M+IDEG+1
    INTEGER, PARAMETER :: N=3, LWORK=3*N-1
    REAL(KIND=DP) :: T, WSP(LWSP), V(3,3)
    REAL(KIND=DP) :: W(N), WORK(LWORK), L(3,3)
    INTEGER :: IPIV(M), IEXPH, NS, IFLAG, INFO
    CHARACTER*120 :: MSG
    CHARACTER*8 :: CHARV(1)
    INTEGER :: INTV(1)
    REAL(KIND=DP) :: REALV(1)
    ! ----------------------------------------------------------------------- !
    EXPM_3X3 = ZERO
    IF (ALL(ABS(A) <= EPSILON(A))) THEN
       EXPM_3X3 = EYE(3)
       RETURN
    ELSE IF (ISDIAG(A)) THEN
       EXPM_3X3(1,1) = EXP(A(1,1))
       EXPM_3X3(2,2) = EXP(A(2,2))
       EXPM_3X3(3,3) = EXP(A(3,3))
       RETURN
    END IF

    ! TRY DGPADM (USUALLY GOOD)
    T = ONE
    IFLAG = 0
    CALL DGPADM(IDEG, M, T, A, LDH, WSP, LWSP, IPIV, IEXPH, NS, IFLAG)
    IF (IFLAG >= 0) THEN
       EXPM_3X3 = RESHAPE(WSP(IEXPH:IEXPH+M*M-1), SHAPE(EXPM_3X3))
       RETURN
    END IF

    ! PROBLEM WITH DGPADM, USE OTHER METHOD
    IF (IFLAG == -8) THEN
       MSG = 'TENSALG.EXPM: BAD SIZES (IN INPUT OF DGPADM)'
    ELSE IF (IFLAG == -9) THEN
       MSG = 'TENSALG.EXPM: ERROR - NULL H IN INPUT OF DGPADM.'
    ELSE IF (IFLAG == -7) THEN
       MSG = 'TENSALG.EXPM: PROBLEM IN DGESV (WITHIN DGPADM)'
    END IF
    CALL TENSERR(IERR, MSG, INTV, REALV, CHARV)
    V = A
    CALL DSYEV("V", "L", 3, V, 3, W, WORK, LWORK, INFO)
    L = ZERO
    L(1,1) = EXP(W(1))
    L(2,2) = EXP(W(2))
    L(3,3) = EXP(W(3))
    EXPM_3X3 = MATMUL(MATMUL(V, L ), TRANSPOSE(V))
    RETURN
  END FUNCTION EXPM_3X3

  ! ************************************************************************* !
  ! THE FOLLOWING FUNCTIONS DEFINE THE DOT PRODUCT OF TWO TENSORS
  !             C = A.B
  ! TENSORS CAN BE STORED AS 6X1 OR 3X3. THE PARAMETERS TO EACH FUNCTION ARE:
  !             [LR]A = LEFT|RIGHT ARRAY
  !             [LR]M = LEFT|RIGHT MATRIX
  ! ************************************************************************* !

  FUNCTION D_LA_RM(LA, RM)
    REAL(KIND=DP), INTENT(IN) :: LA(6), RM(3,3)
    REAL(KIND=DP) :: D_LA_RM(3,3)
    D_LA_RM(1,1) = LA(1)*RM(1,1)+LA(4)*RM(2,1)+LA(5)*RM(3,1)
    D_LA_RM(1,2) = LA(1)*RM(1,2)+LA(4)*RM(2,2)+LA(5)*RM(3,2)
    D_LA_RM(1,3) = LA(1)*RM(1,3)+LA(4)*RM(2,3)+LA(5)*RM(3,3)
    D_LA_RM(2,1) = LA(2)*RM(2,1)+LA(4)*RM(1,1)+LA(6)*RM(3,1)
    D_LA_RM(2,2) = LA(2)*RM(2,2)+LA(4)*RM(1,2)+LA(6)*RM(3,2)
    D_LA_RM(2,3) = LA(2)*RM(2,3)+LA(4)*RM(1,3)+LA(6)*RM(3,3)
    D_LA_RM(3,1) = LA(3)*RM(3,1)+LA(5)*RM(1,1)+LA(6)*RM(2,1)
    D_LA_RM(3,2) = LA(3)*RM(3,2)+LA(5)*RM(1,2)+LA(6)*RM(2,2)
    D_LA_RM(3,3) = LA(3)*RM(3,3)+LA(5)*RM(1,3)+LA(6)*RM(2,3)
    RETURN
  END FUNCTION D_LA_RM

  FUNCTION D_LM_RA(LM, RA)
    REAL(KIND=DP), INTENT(IN) :: LM(3,3), RA(6)
    REAL(KIND=DP) :: D_LM_RA(3,3)
    D_LM_RA(1,1) = RA(1)*LM(1,1)+RA(4)*LM(1,2)+RA(5)*LM(1,3)
    D_LM_RA(1,2) = RA(2)*LM(1,2)+RA(4)*LM(1,1)+RA(6)*LM(1,3)
    D_LM_RA(1,3) = RA(3)*LM(1,3)+RA(5)*LM(1,1)+RA(6)*LM(1,2)
    D_LM_RA(2,1) = RA(1)*LM(2,1)+RA(4)*LM(2,2)+RA(5)*LM(2,3)
    D_LM_RA(2,2) = RA(2)*LM(2,2)+RA(4)*LM(2,1)+RA(6)*LM(2,3)
    D_LM_RA(2,3) = RA(3)*LM(2,3)+RA(5)*LM(2,1)+RA(6)*LM(2,2)
    D_LM_RA(3,1) = RA(1)*LM(3,1)+RA(4)*LM(3,2)+RA(5)*LM(3,3)
    D_LM_RA(3,2) = RA(2)*LM(3,2)+RA(4)*LM(3,1)+RA(6)*LM(3,3)
    D_LM_RA(3,3) = RA(3)*LM(3,3)+RA(5)*LM(3,1)+RA(6)*LM(3,2)
    RETURN
  END FUNCTION D_LM_RA

  FUNCTION D_LM_RM(LM, RM)
    REAL(KIND=DP), INTENT(IN) :: LM(3,3), RM(3,3)
    REAL(KIND=DP) :: D_LM_RM(3,3)
    D_LM_RM(1,1) = LM(1,1)*RM(1,1)+LM(1,2)*RM(2,1)+LM(1,3)*RM(3,1)
    D_LM_RM(1,2) = LM(1,1)*RM(1,2)+LM(1,2)*RM(2,2)+LM(1,3)*RM(3,2)
    D_LM_RM(1,3) = LM(1,1)*RM(1,3)+LM(1,2)*RM(2,3)+LM(1,3)*RM(3,3)
    D_LM_RM(2,1) = LM(2,1)*RM(1,1)+LM(2,2)*RM(2,1)+LM(2,3)*RM(3,1)
    D_LM_RM(2,2) = LM(2,1)*RM(1,2)+LM(2,2)*RM(2,2)+LM(2,3)*RM(3,2)
    D_LM_RM(2,3) = LM(2,1)*RM(1,3)+LM(2,2)*RM(2,3)+LM(2,3)*RM(3,3)
    D_LM_RM(3,1) = LM(3,1)*RM(1,1)+LM(3,2)*RM(2,1)+LM(3,3)*RM(3,1)
    D_LM_RM(3,2) = LM(3,1)*RM(1,2)+LM(3,2)*RM(2,2)+LM(3,3)*RM(3,2)
    D_LM_RM(3,3) = LM(3,1)*RM(1,3)+LM(3,2)*RM(2,3)+LM(3,3)*RM(3,3)
    RETURN
  END FUNCTION D_LM_RM

  FUNCTION D_LA_RA(LA, RA)
    REAL(KIND=DP), INTENT(IN) :: LA(6), RA(6)
    REAL(KIND=DP) :: D_LA_RA(6)
    D_LA_RA(1) = LA(1)*RA(1)+LA(4)*RA(4)+LA(5)*RA(5)
    D_LA_RA(2) = LA(2)*RA(2)+LA(4)*RA(4)+LA(6)*RA(6)
    D_LA_RA(3) = LA(3)*RA(3)+LA(5)*RA(5)+LA(6)*RA(6)
    D_LA_RA(4) = LA(1)*RA(4)+LA(4)*RA(2)+LA(5)*RA(6)
    D_LA_RA(5) = LA(1)*RA(5)+LA(4)*RA(6)+LA(5)*RA(3)
    D_LA_RA(6) = LA(2)*RA(6)+LA(4)*RA(5)+LA(6)*RA(3)
  END FUNCTION D_LA_RA

  ! ************************************************************************* !

  FUNCTION DYAD(A, B)
    ! ----------------------------------------------------------------------- !
    ! DYADIC PRODUCT OF A AND B
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP), INTENT(IN) :: A(:), B(:)
    REAL(KIND=DP) :: DYAD(SIZE(A),SIZE(A))
    INTEGER :: I, J
    FORALL(I=1:SIZE(A), J=1:SIZE(A)) DYAD(I,J) = A(I) * B(J)
    RETURN
  END FUNCTION DYAD

  ! ************************************************************************* !

  FUNCTION PUSH_6X6(F, RM)
    ! ----------------------------------------------------------------------- !
    ! PUSH TRANSFORMATION OF RM
    ! PUSH: RM' = 1/J F.F.RM.FT.FT
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP), INTENT(IN) :: F(3,3), RM(6,6)
    REAL(KIND=DP) :: PUSH_6X6(6,6)
    REAL(KIND=DP) :: JAC, Q(6,6)
    JAC = DET_3X3(F)
    Q = SYMLEAFF(F)
    PUSH_6X6 = MATMUL(MATMUL(Q, RM), TRANSPOSE(Q)) / JAC
    RETURN
  END FUNCTION PUSH_6X6

  ! ************************************************************************* !

  FUNCTION PUSH_6X1(F, RA)
    ! ----------------------------------------------------------------------- !
    ! PUSH TRANSFORMATION OF RA
    ! PUSH: RA' = 1/J F.RA.FT
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP), INTENT(IN) :: F(3,3), RA(6)
    REAL(KIND=DP) :: PUSH_6X1(6)
    REAL(KIND=DP) :: JAC
    JAC = DET_3X3(F)
    PUSH_6X1(1) = (F(1,1)*(F(1,1)*RA(1) + F(1,2)*RA(4) + F(1,3)*RA(5)) + &
                   F(1,2)*(F(1,1)*RA(4) + F(1,2)*RA(2) + F(1,3)*RA(6)) + &
                   F(1,3)*(F(1,1)*RA(5) + F(1,2)*RA(6) + F(1,3)*RA(3))) / JAC
    PUSH_6X1(2) = (F(2,1)*(F(2,1)*RA(1) + F(2,2)*RA(4) + F(2,3)*RA(5)) + &
                   F(2,2)*(F(2,1)*RA(4) + F(2,2)*RA(2) + F(2,3)*RA(6)) + &
                   F(2,3)*(F(2,1)*RA(5) + F(2,2)*RA(6) + F(2,3)*RA(3))) / JAC
    PUSH_6X1(3) = (F(3,1)*(F(3,1)*RA(1) + F(3,2)*RA(4) + F(3,3)*RA(5)) + &
                   F(3,2)*(F(3,1)*RA(4) + F(3,2)*RA(2) + F(3,3)*RA(6)) + &
                   F(3,3)*(F(3,1)*RA(5) + F(3,2)*RA(6) + F(3,3)*RA(3))) / JAC
    PUSH_6X1(4) = (F(2,1)*(F(1,1)*RA(1) + F(1,2)*RA(4) + F(1,3)*RA(5)) + &
                   F(2,2)*(F(1,1)*RA(4) + F(1,2)*RA(2) + F(1,3)*RA(6)) + &
                   F(2,3)*(F(1,1)*RA(5) + F(1,2)*RA(6) + F(1,3)*RA(3))) / JAC
    PUSH_6X1(5) = (F(3,1)*(F(1,1)*RA(1) + F(1,2)*RA(4) + F(1,3)*RA(5)) + &
                   F(3,2)*(F(1,1)*RA(4) + F(1,2)*RA(2) + F(1,3)*RA(6)) + &
                   F(3,3)*(F(1,1)*RA(5) + F(1,2)*RA(6) + F(1,3)*RA(3))) / JAC
    PUSH_6X1(6) = (F(3,1)*(F(2,1)*RA(1) + F(2,2)*RA(4) + F(2,3)*RA(5)) + &
                   F(3,2)*(F(2,1)*RA(4) + F(2,2)*RA(2) + F(2,3)*RA(6)) + &
                   F(3,3)*(F(2,1)*RA(5) + F(2,2)*RA(6) + F(2,3)*RA(3))) / JAC
    RETURN
  END FUNCTION PUSH_6X1

  FUNCTION PUSH_3X3(F, RM3)
    ! ----------------------------------------------------------------------- !
    ! PUSH TRANSFORMATION OF RM3
    ! PUSH: RM3' = 1/J F.RM3.FT
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP), INTENT(IN) :: F(3,3), RM3(3,3)
    REAL(KIND=DP) :: PUSH_3X3(3,3)
    REAL(KIND=DP) :: JAC
    JAC = DET_3X3(F)
    PUSH_3X3 = MATMUL(MATMUL(F, RM3), TRANSPOSE(F)) / JAC
    RETURN
  END FUNCTION PUSH_3X3

  ! ************************************************************************* !

  FUNCTION PULL_6X1(F, RA)
    ! ----------------------------------------------------------------------- !
    ! PULL TRANSFORMATION OF RA
    ! PULL: RA' = J FI.RA.FIT
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP), INTENT(IN) :: F(3,3), RA(6)
    REAL(KIND=DP) :: PULL_6X1(6)
    REAL(KIND=DP) :: FI(3,3)
    FI = INV_3X3(F)
    PULL_6X1 = PUSH_6X1(FI, RA)
    RETURN
  END FUNCTION PULL_6X1

  FUNCTION PULL_3X3(F, RM)
    ! ----------------------------------------------------------------------- !
    ! PULL TRANSFORMATION OF RM
    ! PULL: RM' = J FI.RM.FIT
    ! ----------------------------------------------------------------------- !
    REAL(KIND=DP), INTENT(IN) :: F(3,3), RM(3,3)
    REAL(KIND=DP) :: PULL_3X3(3,3)
    REAL(KIND=DP) :: FI(3,3)
    FI = INV_3X3(F)
    PULL_3X3 = PUSH_3X3(FI, RM)
    RETURN
  END FUNCTION PULL_3X3

  ! ************************************************************************* !

  SUBROUTINE INVARS_6X1(A, I1, I2, I3)
    ! ----------------------------------------------------------------------- !
    ! INVARIANTS OF SYMMETRIC SECOND ORDER TENSOR A
    ! ----------------------------------------------------------------------- !
    REAL(DP), INTENT(IN) :: A(6)
    REAL(DP), INTENT(OUT) :: I1, I2
    REAL(DP), INTENT(OUT), OPTIONAL :: I3
    REAL(DP) :: TRASQ
    I1 = TR_6X1(A)
    TRASQ = DBD_6X1(A, A)
    I2 = HALF * (I1 ** 2 - TRASQ)
    IF (PRESENT(I3)) I3 = DET_6X1(A)
  END SUBROUTINE INVARS_6X1

  ! ************************************************************************* !


  SUBROUTINE TENSERR(I, MSG, INTV, REALV, CHARV)
    ! ----------------------------------------------------------------------- !
    ! ERROR HANDLING
    ! ----------------------------------------------------------------------- !
    INTEGER, INTENT(IN) :: I, INTV(*)
    CHARACTER*120, INTENT(IN) :: MSG
    REAL(KIND=DP), INTENT(IN) :: REALV(*)
    CHARACTER*8, INTENT(IN) :: CHARV(1)
    CALL STDB_ABQERR(I, MSG, INTV, REALV, CHARV)
  END SUBROUTINE TENSERR

END MODULE TENSALG
