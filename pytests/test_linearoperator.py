import pytest

import numpy as np
from numpy.testing import assert_array_equal, assert_array_almost_equal

from pylops import LinearOperator
from pylops.basicoperators import MatrixMult, VStack, HStack, Diagonal, Zero

par1 = {'ny': 11, 'nx': 11,
        'imag': 0, 'dtype':'float32'}  # square real
par2 = {'ny': 21, 'nx': 11,
        'imag': 0, 'dtype':'float32'}  # overdetermined real
par1j = {'ny': 11, 'nx': 11,
         'imag': 1j, 'dtype':'complex64'} # square imag
par2j = {'ny': 21, 'nx': 11,
         'imag': 1j, 'dtype': 'complex64'}  # overdetermined imag


@pytest.mark.parametrize("par", [(par1), (par2), (par1j)])
def test_overloads(par):
    """Apply various overloaded operators (.H, -, +, *) and ensure that the
    returned operator is still of pylops LinearOperator type
    """
    diag = np.arange(par['nx']) +\
           par['imag'] * np.arange(par['nx'])
    Dop = Diagonal(diag, dtype=par['dtype'])

    # .H
    assert isinstance(Dop.H, LinearOperator)
    # negate
    assert isinstance(-Dop, LinearOperator)
    # multiply by scalar
    assert isinstance(2*Dop, LinearOperator)
    # +
    assert isinstance(Dop + Dop, LinearOperator)
    # -
    assert isinstance(Dop - 2*Dop, LinearOperator)
    # *
    assert isinstance(Dop * Dop, LinearOperator)
    # **
    assert isinstance(Dop **2, LinearOperator)


@pytest.mark.parametrize("par", [(par1), (par1j)])
def test_scaled(par):
    """Verify that _ScaledLinearOperator produces the correct type based
    on its inputs types
    """
    dtypes = [np.float32, np.float64]
    for dtype in dtypes:
        diag = np.arange(par['nx'], dtype=dtype) + \
               par['imag'] * np.arange(par['nx'], dtype=dtype)
        Dop = Diagonal(diag, dtype=dtype)
        Sop = 3. * Dop
        S1op = -3. * Dop
        S2op = Dop * 3.
        S3op = Dop * -3.
        assert Sop.dtype == dtype
        assert S1op.dtype == dtype
        assert S2op.dtype == dtype
        assert S3op.dtype == dtype


@pytest.mark.parametrize("par", [(par1), (par1j)])
def test_dense(par):
    """Dense matrix representation of square matrix
    """
    diag = np.arange(par['nx']) + par['imag'] * np.arange(par['nx'])
    D = np.diag(diag)
    Dop = Diagonal(diag, dtype=par['dtype'])
    assert_array_equal(Dop.todense(), D)


@pytest.mark.parametrize("par", [(par1), (par1j)])
def test_dense_skinny(par):
    """Dense matrix representation of skinny matrix
    """
    diag = np.arange(par['nx']) + par['imag'] * np.arange(par['nx'])
    D = np.diag(diag)
    Dop = Diagonal(diag, dtype=par['dtype'])
    Zop = Zero(par['nx'], 3, dtype=par['dtype'])
    Op = HStack([Dop, Zop])
    O = np.hstack((D, np.zeros((par['nx'], 3))))
    assert_array_equal(Op.todense(), O)


@pytest.mark.parametrize("par", [(par1), (par2), (par1j)])
def test_sparse(par):
    """Sparse matrix representation
    """
    diag = np.arange(par['nx']) +\
           par['imag'] * np.arange(par['nx'])
    D = np.diag(diag)
    Dop = Diagonal(diag, dtype=par['dtype'])
    S = Dop.tosparse()
    assert_array_equal(S.A, D)


@pytest.mark.parametrize("par", [(par1), (par2), (par1j)])
def test_eigs(par):
    """Eigenvalues and condition number estimate with ARPACK
    """
    # explicit=True
    diag = np.arange(par['nx'], 0, -1) + \
           par['imag'] * np.arange(par['nx'], 0, -1)
    Op = MatrixMult(np.vstack((np.diag(diag),
                               np.zeros((par['ny'] - par['nx'], par['nx'])))))
    eigs = Op.eigs()
    assert_array_almost_equal(diag[:eigs.size], eigs, decimal=3)

    cond = Op.cond()
    assert_array_almost_equal(np.real(cond), par['nx'], decimal=3)

    # explicit=False
    Op = Diagonal(diag, dtype=par['dtype'])
    if par['ny'] > par['nx']:
        Op = VStack([Op, Zero(par['ny'] - par['nx'], par['nx'])])
    eigs = Op.eigs()
    assert_array_almost_equal(diag[:eigs.size], eigs, decimal=3)

    # uselobpcg cannot be used for square non-symmetric complex matrices
    if np.iscomplex(Op):
        eigs1 = Op.eigs(uselobpcg=True)
        assert_array_almost_equal(eigs, eigs1, decimal=3)

    cond = Op.cond()
    assert_array_almost_equal(np.real(cond), par['nx'], decimal=3)

    if np.iscomplex(Op):
        cond1 = Op.cond(uselobpcg=True, niter=100)
        assert_array_almost_equal(np.real(cond), np.real(cond1), decimal=3)


@pytest.mark.parametrize("par", [(par1), (par2), (par1j), (par2j)])
def test_conj(par):
    """Complex conjugation operator
    """
    M = 1j * np.ones((par['ny'], par['nx']))
    Op = MatrixMult(M, dtype=np.complex)
    Opconj = Op.conj()

    x = np.arange(par['nx']) + \
        par['imag'] * np.arange(par['nx'])
    y = Opconj * x

    # forward
    assert_array_almost_equal(Opconj * x, np.dot(M.conj(), x))

    # adjoint
    assert_array_almost_equal(Opconj.H * y, np.dot(M.T, y))


@pytest.mark.parametrize("par", [(par1), (par2)])
def test_apply_columns_explicit(par):
    """Apply columns to explicit and non-explicit operator
    """
    M = np.ones((par['ny'], par['nx']))
    Mop = MatrixMult(M, dtype=par['dtype'])
    M1op = MatrixMult(M, dtype=par['dtype'])
    M1op.explicit = False
    cols = np.sort(np.random.permutation(np.arange(par['nx']))[:par['nx']//2])

    Mcols = M[:, cols]
    Mcolsop = Mop.apply_columns(cols)
    M1colsop = M1op.apply_columns(cols)

    x = np.arange(len(cols))
    y = np.arange(par['ny'])

    # forward
    assert_array_almost_equal(Mcols @ x, Mcolsop.matvec(x))
    assert_array_almost_equal(Mcols @ x, M1colsop.matvec(x))

    # adjoint
    assert_array_almost_equal(Mcols.T @ y, Mcolsop.rmatvec(y))
    assert_array_almost_equal(Mcols.T @ y, M1colsop.rmatvec(y))


@pytest.mark.parametrize("par", [(par1), (par2), (par1j), (par2j)])
def test_realimag(par):
    """Real/imag operator
    """
    M = np.random.normal(0, 1, (par['ny'], par['nx'])) + \
        1j * np.random.normal(0, 1, (par['ny'], par['nx']))
    Op = MatrixMult(M, dtype=np.complex)

    Opr = Op.toreal()
    Opi = Op.toimag()

    # forward
    x = np.arange(par['nx'])
    y = Op * x
    yr = Opr * x
    yi = Opi * x

    assert_array_equal(np.real(y), yr)
    assert_array_equal(np.imag(y), yi)

    # adjoint
    y = np.arange(par['ny']) + 1j * np.arange(par['ny'])
    x = Op.H * y
    xr = Opr.H * y
    xi = Opi.H * y

    assert_array_equal(np.real(x), xr)
    assert_array_equal(np.imag(x), -xi)
