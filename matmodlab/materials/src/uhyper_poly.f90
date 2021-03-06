subroutine uhyper(BI1, BI2, Jac, U, DU, D2U, D3U, temp, noel, cmname, &
     incmpflag, nstatev, statev, nfieldv, fieldv, fieldvinc, &
     nprop, props)
  ! ----------------------------------------------------------------------- !
  ! HYPERELASTIC POLYNOMIAL MODEL
  ! ----------------------------------------------------------------------- !
  implicit none
  character*8, intent(in) :: cmname
  integer, parameter :: dp=selected_real_kind(14)
  integer, intent(in) :: nprop, noel, nstatev, incmpflag, nfieldv
  real(kind=dp), intent(in) :: BI1, BI2, Jac, props(nprop), temp
  real(kind=dp), intent(inout) :: U(2), DU(3), D2U(6), D3U(6), statev(nstatev)
  real(kind=dp), intent(inout) :: fieldv(nfieldv), fieldvinc(nfieldv)
  real(kind=dp) :: xp(nprop)
  ! ----------------------------------------------------------------------- !
  xp = props

  ! ---------------------------------------------------------------- Energies
  u = 0.
  u(2) = u(2) + xp(1) * ((BI1 - 3.) ** 1) * ((BI2 - 3.) ** 0)
  u(2) = u(2) + xp(2) * ((BI1 - 3.) ** 0) * ((BI2 - 3.) ** 1)
  u(2) = u(2) + xp(3) * ((BI1 - 3.) ** 2) * ((BI2 - 3.) ** 0)
  u(2) = u(2) + xp(4) * ((BI1 - 3.) ** 1) * ((BI2 - 3.) ** 1)
  u(2) = u(2) + xp(5) * ((BI1 - 3.) ** 0) * ((BI2 - 3.) ** 2)
  u(2) = u(2) + xp(6) * ((BI1 - 3.) ** 3) * ((BI2 - 3.) ** 0)
  u(2) = u(2) + xp(7) * ((BI1 - 3.) ** 2) * ((BI2 - 3.) ** 1)
  u(2) = u(2) + xp(8) * ((BI1 - 3.) ** 1) * ((BI2 - 3.) ** 2)
  u(2) = u(2) + xp(9) * ((BI1 - 3.) ** 0) * ((BI2 - 3.) ** 3)
  if (xp(10) > 0.) u(1) = u(1) + 1. / xp(10) * (Jac - 1.) ** 2
  if (xp(11) > 0.) u(1) = u(1) + 1. / xp(11) * (Jac - 1.) ** 4
  if (xp(12) > 0.) u(1) = u(1) + 1. / xp(12) * (Jac - 1.) ** 6
  u(1) = u(1) + u(2)

  ! ------------------------------------------------------- First Derivatives
  DU = 0.
  DU(1) = DU(1) + 1.0 * xp(1) * ((BI1 - 3.) ** 0) * ((BI2 - 3.) ** 0)
  DU(2) = DU(2) + 1.0 * xp(2) * ((BI1 - 3.) ** 0) * ((BI2 - 3.) ** 0)
  DU(1) = DU(1) + 2.0 * xp(3) * ((BI1 - 3.) ** 1) * ((BI2 - 3.) ** 0)
  DU(1) = DU(1) + 1.0 * xp(4) * ((BI1 - 3.) ** 0) * ((BI2 - 3.) ** 1)
  DU(2) = DU(2) + 1.0 * xp(4) * ((BI1 - 3.) ** 1) * ((BI2 - 3.) ** 0)
  DU(2) = DU(2) + 2.0 * xp(5) * ((BI1 - 3.) ** 0) * ((BI2 - 3.) ** 1)
  DU(1) = DU(1) + 3.0 * xp(6) * ((BI1 - 3.) ** 2) * ((BI2 - 3.) ** 0)
  DU(1) = DU(1) + 2.0 * xp(7) * ((BI1 - 3.) ** 1) * ((BI2 - 3.) ** 1)
  DU(2) = DU(2) + 1.0 * xp(7) * ((BI1 - 3.) ** 2) * ((BI2 - 3.) ** 0)
  DU(1) = DU(1) + 1.0 * xp(8) * ((BI1 - 3.) ** 0) * ((BI2 - 3.) ** 2)
  DU(2) = DU(2) + 2.0 * xp(8) * ((BI1 - 3.) ** 1) * ((BI2 - 3.) ** 1)
  DU(2) = DU(2) + 3.0 * xp(9) * ((BI1 - 3.) ** 0) * ((BI2 - 3.) ** 2)
  if (xp(10) > 0.) DU(3) = DU(3) + 2.0 / xp(10) * (Jac - 1.) ** 1
  if (xp(11) > 0.) DU(3) = DU(3) + 4.0 / xp(11) * (Jac - 1.) ** 3
  if (xp(12) > 0.) DU(3) = DU(3) + 6.0 / xp(12) * (Jac - 1.) ** 5

  ! ------------------------------------------------------ Second Derivatives
  D2U = 0.
  D2U(1) = D2U(1) + 2.0 * xp(3) * ((BI1 - 3.) ** 0) * ((BI2 - 3.) ** 0)
  D2U(4) = D2U(4) + 1.0 * xp(4) * ((BI1 - 3.) ** 0) * ((BI2 - 3.) ** 0)
  D2U(2) = D2U(2) + 2.0 * xp(5) * ((BI1 - 3.) ** 0) * ((BI2 - 3.) ** 0)
  D2U(1) = D2U(1) + 6.0 * xp(6) * ((BI1 - 3.) ** 1) * ((BI2 - 3.) ** 0)
  D2U(1) = D2U(1) + 2.0 * xp(7) * ((BI1 - 3.) ** 0) * ((BI2 - 3.) ** 1)
  D2U(4) = D2U(4) + 2.0 * xp(7) * ((BI1 - 3.) ** 1) * ((BI2 - 3.) ** 0)
  D2U(2) = D2U(2) + 2.0 * xp(8) * ((BI1 - 3.) ** 1) * ((BI2 - 3.) ** 0)
  D2U(4) = D2U(4) + 2.0 * xp(8) * ((BI1 - 3.) ** 0) * ((BI2 - 3.) ** 1)
  D2U(2) = D2U(2) + 6.0 * xp(9) * ((BI1 - 3.) ** 0) * ((BI2 - 3.) ** 1)
  if (xp(10) > 0.) D2U(3) = D2U(3) + 2.0 / xp(10) * (Jac - 1.) ** 0
  if (xp(11) > 0.) D2U(3) = D2U(3) + 12.0 / xp(11) * (Jac - 1.) ** 2
  if (xp(12) > 0.) D2U(3) = D2U(3) + 30.0 / xp(12) * (Jac - 1.) ** 4

  ! ------------------------------------------------------- Third Derivatives
  D3U = 0.
  if (xp(11) > 0.) D3U(6) = D3U(6) + 24.0 / xp(11) * (Jac - 1.) ** 1
  if (xp(12) > 0.) D3U(6) = D3U(6) + 120.0 / xp(12) * (Jac - 1.) ** 3

  return
end subroutine uhyper