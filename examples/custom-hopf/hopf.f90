! Supercritical Hopf normal form.
!
!   x' = mu*x - y - x*(x**2 + y**2)
!   y' = x + mu*y - y*(x**2 + y**2)
!
! The equilibrium x=y=0 changes stability at mu=0.  A stable periodic
! orbit with radius sqrt(mu) and period 2*pi exists for mu>0.

      SUBROUTINE FUNC(NDIM,U,ICP,PAR,IJAC,F,DFDU,DFDP)
      IMPLICIT NONE
      INTEGER NDIM, IJAC, ICP(*)
      DOUBLE PRECISION U(NDIM), PAR(*), F(NDIM), DFDU(*), DFDP(*)
      DOUBLE PRECISION X,Y,MU,R2

      X=U(1)
      Y=U(2)
      MU=PAR(1)
      R2=X*X+Y*Y

      F(1)=MU*X-Y-X*R2
      F(2)=X+MU*Y-Y*R2

      END SUBROUTINE FUNC

      SUBROUTINE STPNT(NDIM,U,PAR,T)
      IMPLICIT NONE
      INTEGER NDIM
      DOUBLE PRECISION U(NDIM), PAR(*), T

      PAR(1)=-1.0D0
      U(1)=0.0D0
      U(2)=0.0D0

      END SUBROUTINE STPNT

      SUBROUTINE BCND
      END SUBROUTINE BCND

      SUBROUTINE ICND
      END SUBROUTINE ICND

      SUBROUTINE FOPT
      END SUBROUTINE FOPT

      SUBROUTINE PVLS
      END SUBROUTINE PVLS
