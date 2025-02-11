import warnings
from typing import Tuple

import numpy as np
from scipy.interpolate import interpn, interp1d

from .checks import num_dim2
from .conversion import scale_time
from .tictoc import TicToc


def expand_matrix(matrix, exp_coeff, edge_val=None):
    """
        Enlarge a matrix by extending the edge values.

        expandMatrix enlarges an input matrix by extension of the values at
        the outer faces of the matrix (endpoints in 1D, outer edges in 2D,
        outer surfaces in 3D). Alternatively, if an input for edge_val is
        given, all expanded matrix elements will have this value. The values
        for exp_coeff are forced to be real positive integers (or zero).

        Note, indexing is done inline with other k-Wave functions using
        mat(x) in 1D, mat(x, y) in 2D, and mat(x, y, z) in 3D.
    Args:
        matrix: the matrix to enlarge
        exp_coeff: the number of elements to add in each dimension
                    in 1D: [a] or [x_start, x_end]
                    in 2D: [a] or [x, y] or
                           [x_start, x_end, y_start, y_end]
                    in 3D: [a] or [x, y, z] or
                           [x_start, x_end, y_start, y_end, z_start, z_end]
                           (here 'a' is applied to all dimensions)
        edge_val: value to use in the matrix expansion
    Returns:
        expanded matrix
    """

    opts = {}
    matrix = np.squeeze(matrix)

    if edge_val is None:
        opts['mode'] = 'edge'
    else:
        opts['mode'] = 'constant'
        opts['constant_values'] = edge_val

    exp_coeff = np.array(exp_coeff).astype(int).squeeze()
    n_coeff = exp_coeff.size
    assert n_coeff > 0

    if n_coeff == 1:
        opts['pad_width'] = exp_coeff
    elif len(matrix.shape) == 1:
        assert n_coeff <= 2
        opts['pad_width'] = exp_coeff
    elif len(matrix.shape) == 2:
        if n_coeff == 2:
            opts['pad_width'] = exp_coeff
        if n_coeff == 4:
            opts['pad_width'] = [(exp_coeff[0], exp_coeff[1]), (exp_coeff[2], exp_coeff[3])]
    elif len(matrix.shape) == 3:
        if n_coeff == 3:
            opts['pad_width'] = np.tile(np.expand_dims(exp_coeff, axis=-1), [1, 2])
        if n_coeff == 6:
            opts['pad_width'] = [(exp_coeff[0], exp_coeff[1]), (exp_coeff[2], exp_coeff[3]), (exp_coeff[4], exp_coeff[5])]

    return np.pad(matrix, **opts)


def resize(mat, new_size, interp_mode='linear'):
    """
    resize: resamples a "matrix" of spatial samples to a desired "resolution" or spatial sampling frequency via interpolation

    Args:
        mat:                matrix to be "resized" i.e. resampled
        new_size:         desired output resolution
        interp_mode:        interpolation method

    Returns:
        res_mat:            "resized" matrix

    """

    # start the timer
    TicToc.tic()

    # update command line status
    print('Resizing matrix...')

    # check inputs
    assert num_dim2(mat) == len(new_size), \
        'Resolution input must have the same number of elements as data dimensions.'

    mat = mat.squeeze()
    mat_shape = mat.shape

    axis = []
    for dim in range(len(mat.shape)):
        dim_size = mat.shape[dim]
        axis.append(np.linspace(0, 1, dim_size))

    new_axis = []
    for dim in range(len(new_size)):
        dim_size = new_size[dim]
        new_axis.append(np.linspace(0, 1, dim_size))

    points = tuple(p for p in axis)
    xi = np.meshgrid(*new_axis)
    xi = np.array([x.flatten() for x in xi]).T
    new_points = xi
    mat_rs = np.squeeze(interpn(points, mat, new_points, method=interp_mode))
    # TODO: fix this hack.
    if dim + 1 == 3:
        mat_rs = mat_rs.reshape([new_size[1], new_size[0], new_size[2]])
        mat_rs = np.transpose(mat_rs, (1, 0, 2))
    else:
        mat_rs = mat_rs.reshape(new_size, order='F')
    # update command line status
    print(f'  completed in {scale_time(TicToc.toc())}')
    assert mat_rs.shape == tuple(new_size), "Resized matrix does not match requested size."
    return mat_rs


def gradient_fd(f, dx=None, dim=None, deriv_order=None, accuracy_order=None):
    """
    A wrapper of the numpy gradient method for use in the k-wave library.

    gradient_fd calculates the gradient of an n-dimensional input matrix
    using the finite-difference method. For one-dimensional inputs, the
    gradient is always computed along the non-singleton dimension. For
    higher dimensional inputs, the gradient for singleton dimensions is
    returned as 0. For elements in the centre of the grid, the gradient
    is computed using centered finite-differences. For elements on the
    edge of the grid, the gradient is computed using forward or backward
    finite-differences. The order of accuracy of the finite-difference
    approximation is controlled by accuracy_order (default = 2). The
    calculations are done using sparse multiplication, so the input
    matrix is always cast to double precision.

    Args:
        f:
        dx:                 array of values for the grid point spacing in each
                            dimension. If a value for dim is given, dn is the
                            spacing in dimension dim.
        dim:                optional input to specify a single dimension over which to compute the gradient for
                            n-dimension input functions
        deriv_order:        order of the derivative to compute, e.g., use 1 to
                            compute df/dx, 2 to compute df^2/dx^2, etc.
                            (default = 1)
        accuracy_order:     order of accuracy for the finite difference
                            coefficients. Because centered differences are
                            used, this must be set to an integer multiple of
                            2 (default = 2)

    Returns:
        fx, fy, ...         gradient

    """

    if deriv_order:
        warnings.warn("deriv_order is no longer a supported argument.", DeprecationWarning)
    if accuracy_order:
        warnings.warn("accuracy_order is no longer a supported argument.", DeprecationWarning)

    if dim is not None and dx is not None:
        return np.gradient(f, dx, axis=dim)
    elif dim is not None:
        return np.gradient(f, axis=dim)
    elif dx is not None:
        return np.gradient(f, dx)
    else:
        return np.gradient(f)


def min_nd(matrix: np.ndarray) -> Tuple[float, Tuple]:
    min_val, linear_index = np.min(matrix), matrix.argmin()
    numpy_index = np.unravel_index(linear_index, matrix.shape)
    matlab_index = tuple(idx + 1 for idx in numpy_index)
    return min_val, matlab_index


def max_nd(matrix: np.ndarray) -> Tuple[float, Tuple]:
    """
    Returns the maximum value in a n-dimensional array and its index.

    Args:
        matrix (np.ndarray): n-dimensional array of values.

    Returns:
        A tuple containing the maximum value in the array, and a tuple containing the index of the
        maximum value. The index is given in the MATLAB convention, where indexing starts at 1.

    """
    # Get the maximum value and its linear index
    max_val, linear_index = np.max(matrix), matrix.argmax()

    # Convert the linear index to a tuple of indices in the original matrix
    numpy_index = np.unravel_index(linear_index, matrix.shape)

    # Convert the tuple of indices to 1-based indices (as used in Matlab)
    matlab_index = tuple(idx + 1 for idx in numpy_index)

    # Return the maximum value and the 1-based index
    return max_val, matlab_index


def broadcast_axis(data: np.ndarray, ndims: int, axis: int) -> np.ndarray:
    """Broadcast the given axis of the data to the specified number of dimensions.

    Args:
        data (np.ndarray): The data to broadcast.
        ndims (int): The number of dimensions to broadcast the axis to.
        axis (int): The axis to broadcast.

    Returns:
        The broadcasted data.
    """
    newshape = [1] * ndims
    newshape[axis] = -1
    return data.reshape(*newshape)


def revolve2d(mat2D):
    # start timer
    TicToc.tic()

    # update command line status
    print('Revolving 2D matrix to form a 3D matrix...')

    # get size of matrix
    m, n = mat2D.shape

    # create the reference axis for the 2D image
    r_axis_one_sided = np.arange(0, n)
    r_axis_two_sided = np.arange(-(n - 1), n)

    # compute the distance from every pixel in the z-y cross-section of the 3D
    # matrix to the rotation axis
    z, y = np.meshgrid(r_axis_two_sided, r_axis_two_sided)
    r = np.sqrt(y ** 2 + z ** 2)

    # create empty image matrix
    mat3D = np.zeros((m, 2 * n - 1, 2 * n - 1))

    # loop through each cross section and create 3D matrix
    for x_index in range(m):
        interp = interp1d(x=r_axis_one_sided, y=mat2D[x_index, :], kind='linear', bounds_error=False, fill_value=0)
        mat3D[x_index, :, :] = interp(r)

    # update command line status
    print(f'  completed in {scale_time(TicToc.toc())}s')
    return mat3D
