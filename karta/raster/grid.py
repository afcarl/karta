""" Classes for basic grid types """

import sys
import copy
from math import sqrt
import numpy as np
import tiffile          # Temporarily used for TIF IO
import _aai             # Contains the ascread driver
try:
    from fill_sinks import fill_sinks
except ImportError:
    sys.stderr.write("Compiled fill_sinks not available. Falling back to "
                     "Python version\n")
    from raster import fill_sinks
try:
    from scipy.interpolate import griddata
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

class Grid(object):
    """ Grid baseclass. Don't use this directly except to implement subclasses.
    """
    _hdr = {}
    data = np.empty((0,0))

    def __len__(self):
        # Number of bands
        return np.atleast_3d(self.data).shape[2]

    def _check_hdr(self, hdr):
        """ Check that hdr contains required fields. Intended to be overloaded.
        """
        return

    def get_hdr(self):
        """ Return the header dictionary. """
        return self._hdr

    def set_hdr(self, hdr):
        """ Set the header dictionary. """
        self._check_hdr(hdr)
        self._hdr = hdr
        return

    def clipz(self, bounds):
        """ Clip the z-range in place to bounds = [min, max]. """
        self.data = self.data.clip(bounds[0], bounds[1])
        return

    def max(self):
        """ Return the maximum non-nan in self.data. """
        return self.data[np.isnan(self.data)==False].max()

    def min(self):
        """ Return the minimum non-nan in self.data. """
        return self.data[np.isnan(self.data)==False].min()

    def minmax(self):
        """ Return the minimum and maximum value of data array. """
        A = self.data[np.isnan(self.data)==False]
        return (A.min(), A.max())

    def copy(self):
        """ Return a copy. """
        return copy.deepcopy(self)


class RegularGrid(Grid):
    """ Regular (structured) grid class. A RegularGrid contains a fixed number
    of rows and columns with a regular spacing and a scalar or vector field
    defined as `Z`.
    """
    def __init__(self, hdr, Z=None):
        """
        Parameters:
        -----------
        hdr : dictionary of header fields, which must contain
            - xllcorner (float)
            - yllcorner (float)
            - nx (int)
            - ny (int)
            - dx (float)
            - dy (float)
            - nbands (int)
        Z : dependent m-dimensional quantity (nrows x ncols x m)
        """
        if ('nbands' not in hdr) and (Z is not None):
            if Z.ndim >= 3:
                hdr['nbands'] = Z.ndim[2]
            else:
                hdr['nbands'] = 1
        self.set_hdr(hdr)

        shape = (self._hdr['ny'], self._hdr['nx'])
        if Z is None:
            Z = np.empty(shape)
        else:
            if Z.shape[:2] != shape:
                raise GridError('Data array `Z` has an invalid shape')
        self.data = Z
        return

    def _check_hdr(self, hdr):
        """ Check that the header contains the required fields. """
        required_fields = ('xllcorner', 'yllcorner', 'nx', 'ny', 'dx', 'dy',
                           'nbands')
        for key in required_fields:
            if key not in hdr:
                raise GridError('Header missing {0}'.format(key))
        assert isinstance(hdr['nx'], int)
        assert isinstance(hdr['ny'], int)

    def coordmesh(self, *args, **kwargs):
        """ Alias for center_coords() """
        return self.center_coords(*args, **kwargs)

    def center_llref(self):
        """ Return the 'lower-left' reference in terms of a center coordinate.
        """
        return (self._hdr['xllcorner'] + 0.5*self._hdr['dx'],
                self._hdr['yllcorner'] + 0.5*self._hdr['dy'])

    def center_coords(self):
        """ Return the cell-center coordinates. """
        xllcenter, yllcenter = self.center_llref()
        xurcenter = xllcenter + self._hdr['dx'] * (self._hdr['nx'] - 1)
        yurcenter = yllcenter + self._hdr['dy'] * (self._hdr['ny'] - 1)
        return np.meshgrid(np.linspace(xllcenter, xurcenter, self._hdr['nx']),
                           np.linspace(yurcenter, yllcenter, self._hdr['ny']))

    def vertex_coords(self):
        """ Return the coordinates of vertices. """
        xllcorner = self._hdr['xllcorner']
        yllcorner = self._hdr['yllcorner']
        xurcorner = xllcorner + self._hdr['nx'] * self._hdr['dx']
        yurcorner = yllcorner + self._hdr['ny'] * self._hdr['dy']
        nx = self._hdr['nx']
        ny = self._hdr['ny']
        return np.meshgrid(np.linspace(xllcorner, xurcorner, nx + 1),
                           np.linspace(yurcorner, yllcorner, ny + 1))

    def get_region(self, reference='center'):
        """ Return the region characteristics as a tuple, relative to either
        cell centers or the grid edges. """
        if reference == 'center':
            x0, y0  = self.center_llref()
            n = 0
        elif reference == 'edge':
            x0, y0  = self._hdr['xllcorner'], self._hdr['yllcorner']
            n = 1
        else:
            raise GridError("`reference` must be 'center' or 'edge'")
        return (x0, x0 + self._hdr['dx'] * (self._hdr['nx'] + n),
                y0, y0 + self._hdr['dy'] * (self._hdr['ny'] + n))

    def resample(self, dx, dy, method='nearest'):
        """ Resample array in-place to have spacing `dx`, `dy'.

        Parameters
        ----------

        dx : cell dimension, float

        dy : cell dimension, float

        method : interpolation method, string ('nearest', 'linear')
        """
        xllcenter, yllcenter = self.center_llref()
        xurcenter = xllcenter + self._hdr['dx'] * self._hdr['nx']
        yurcenter = yllcenter + self._hdr['dy'] * self._hdr['ny']
        nx = int((xurcenter - xllcenter) // dx)
        ny = int((yurcenter - yllcenter) // dy)

        if HAS_SCIPY:

            xx, yy = self.coordmesh()
            xxi, yyi = np.meshgrid(np.linspace(xllcenter, xurcenter, nx),
                                   np.linspace(yllcenter, yurcenter, ny))
            idata = griddata((xx.flatten(), yy.flatten()), self.data.flatten(),
                             (xxi.flatten(), yyi.flatten()), method=method)
            self.data = idata.reshape(ny, nx)[::-1]

        else:
            dimratio = (dx / self._hdr['dx'], dy / self._hdr['dy'])

            if method == 'nearest':
                JJ, II = np.meshgrid(np.arange(nx), np.arange(ny))
                srcII = np.around(II * dimratio[1]) \
                                .astype(int) \
                                .clip(0, self._hdr['ny'] - 1)
                srcJJ = np.around(JJ * dimratio[0]) \
                                .astype(int).\
                                clip(0, self._hdr['nx'] - 1)
                self.data = self.data[srcII, srcJJ]
            else:
                raise NotImplementedError('method "{0}" not '
                                          'implemented'.format(method))

        hdr = self.get_hdr()
        hdr['dx'] = dx
        hdr['dy'] = dy
        hdr['nx'] = nx
        hdr['ny'] = ny
        self.set_hdr(hdr)
        return

    def resize(self, te):
        """ Resize array to fit within extents given by te. If the new
        dimensions are smaller, the data is clipped. If they are larger,
        nan padding is added.

        *te*        :   tuple of center coordinates in the form
                        (xmin, xmax, ymin, ymax).

        Returns None.
        """
        if self.data is not None:
            xmin1, ymin1 = self.center_llref()
            xmax1 = xmin1 + self._hdr['dx'] * (self._hdr['nx'] - 1)
            ymax1 = ymin1 + self._hdr['dy'] * (self._hdr['ny'] - 1)

            xmin2 = te[0]
            xmax2 = te[1]
            ymin2 = te[2]
            ymax2 = te[3]

            data_a = self.data.copy()
            ny = data_a.shape[0]

            # The left side
            Dx = int(np.floor((xmin2-xmin1) / float(self._hdr['dx'])))
            if Dx < 0:
                data_a = np.hstack([np.nan*np.ones([ny, Dx]), data_a])
            elif Dx > 0:
                data_a = data_a[:,Dx:]
            xllcenter = xmin1 + self._hdr['dx'] * Dx

            # The right side
            Dx = int(np.floor((xmax2-xmax1) / float(self._hdr['dx'])))
            if Dx > 0:
                data_a = np.hstack([data_a, np.nan*np.ones([ny, Dx])])
            elif Dx < 0:
                data_a = data_a[:,:Dx]
            self._hdr['nx'] = data_a.shape[1]

            _, nx = data_a.shape

            # The bottom
            Dy = int(np.ceil((ymin2-ymin1) / float(self._hdr['dy'])))
            if Dy < 0:
                data_a = np.vstack([data_a, np.nan*np.ones([Dy, nx])])
            elif Dy > 0:
                data_a = data_a[Dy:,:]
            yllcenter = ymin1 + self._hdr['dy'] * Dy

            # The top
            Dy = int(np.floor((ymax2-ymax1) / float(self._hdr['dy'])))
            if Dy > 0:
                data_a = np.vstack([np.nan*np.ones([Dy, nx]), data_a])
            elif Dy < 0:
                data_a = data_a[:Dy,:]
            self._hdr['ny'] = data_a.shape[0]

            self.data = data_a
            self._hdr['xllcorner'] = xllcenter - 0.5*self._hdr['dx']
            self._hdr['yllcorner'] = yllcenter - 0.5*self._hdr['dy']

        else:
            raise GridError("no data to resize")
        return

    def get_indices(self, x, y):
        """ Return the column and row indices for the point nearest
        geographical coordinates (x, y). """
        if self.data is None:
            raise GridError('No raster to query')

        x0, y0 = self.center_llref()
        dx = self._hdr['dx']
        dy = self._hdr['dy']
        nx = self._hdr['nx']
        ny = self._hdr['ny']

        xi = np.clip((np.around((np.array(x) - x0) / dx)).astype(int),
                     0, nx-1)
        yi = np.clip(ny - (np.around((np.array(y)-y0) / dy)).astype(int) - 1,
                     0, ny-1)
        return xi, yi

    def sample(self, x, y):
        """ Return the value nearest to (`x`, `y`).
        """
        xi, yi = self.get_indices(x, y)
        nx = self._hdr['nx']
        ny = self._hdr['ny']
        if (np.any(xi < 0) or np.any(xi >= nx) or
            np.any(yi < 0) or np.any(yi >= ny)):
            raise GridError("coordinates ({0}, {1}) are outside grid region "
                            "({2}, {3})".format(xi, yi, nx, ny))
        return self.data[yi, xi]

    def get_profile(self, segments, resolution=10.0):
        """ Sample along a line defined as `segments`. Does not interpolate.

        Parameters:
        -----------
        segments : iterable containing (x,y) pairs
        resolution : sample spacing

        Returns:
        --------
        profile : ndarray
        """

        z = []
        p = 0
        for s, f in zip(segments[:-1], segments[1:]):

            x0 = s[0]
            y0 = s[1]
            xf = f[0]
            yf = f[1]

            xlen = xf-x0
            ylen = yf-y0
            d = sqrt((xf - x0)**2 + (yf - y0)**2)

            while p < d:
                fd = p / d
                fx = fd*xlen
                fy = fd*ylen
                xi, yi = self.get_indices(x0+fx, y0+fy)
                z.append(self.data[yi, xi])
                p += resolution
            p -= d

        return np.array(z)

    def fill_sinks(self):
        """ Fill depressions. Use the algorithm of Wang and Liu (2006). """
        return RegularGrid(copy.copy(self._hdr), Z=fill_sinks(self.data))

    def as_structured(self):
        """ Return a copy as a StructuredGrid instance. This is a more general
        grid class that had a larger memory footprint but can represent more
        flexible data layouts. """
        Xv, Yv = self.vertex_coords()
        return StructuredGrid(Xv, Yv, self.data.copy())

    def aaiwrite(self, f, reference='corner', nodata_value=-9999):
        """ Save internal data as an ASCII grid. Based on the ESRI standard,
        only isometric grids (i.e. `hdr['dx'] == hdr['dy']` can be saved,
        otherwise `GridIOError` is thrown.

        Parameters:
        -----------
        f : either a file-like object or a filename
        reference : specify a header reference ("center" | "corner")
        nodata_value : specify how nans should be represented (int or float)
        """
        if self.data is None:
            raise GridError("no data to write!")

        if reference not in ('center', 'corner'):
            raise GridIOError("reference in AAIGrid.tofile() must be 'center' or "
                           "'corner'")

        if self._hdr['dx'] != self._hdr['dy']:
            raise GridIOError("ASCII grids require isometric grid cells")

        if not hasattr(f, 'read'):
            f = open(f, "w")

        try:
            data_a = self.data.copy()
            data_a[np.isnan(data_a)] = nodata_value

            f.write("NCOLS {0}\n".format(self._hdr['nx']))
            f.write("NROWS {0}\n".format(self._hdr['ny']))
            if reference == 'center':
                d = self._hdr['dx']
                f.write("XLLCENTER {0}\n".format(self._hdr['xllcorner']+0.5*d))
                f.write("YLLCENTER {0}\n".format(self._hdr['yllcorner']+0.5*d))
            elif reference == 'corner':
                f.write("XLLCORNER {0}\n".format(self._hdr['xllcorner']))
                f.write("YLLCORNER {0}\n".format(self._hdr['yllcorner']))
            f.write("CELLSIZE {0}\n".format(self._hdr['dx']))
            f.write("NODATA_VALUE {0}\n".format(nodata_value))
            f.writelines([str(row).replace(',','')[1:-1] +
                            '\n' for row in data_a.tolist()])
        except Exception as e:
            raise e
        finally:
            f.close()
        return

class StructuredGrid(Grid):
    """ Structured Grid class. A StructuredGrid contains a fixed number of rows
    and columns and a scalar or vector field defined on the z-axis. Grid
    spacing is not necessarily regular.
    """

    def __init__(self, hdr=None, X=None, Y=None, Z=None):
        """
        Parameters:
        -----------
        X : first-dimension coordinates of grid nodes
        Y : second-dimension coordinates of grid nodes
        Z : dependent m-dimensional quantity (nrows x ncols x m)
        hdr : (optional) dictionary of header fields, which must contain
            - xllcenter (float)
            - yllcenter (float)
            - nbands (int)
        """
        if True not in (a is None for a in (X,Y,Z)):
            if not (X.shape == Y.shape == Z.shape[:2]):
                raise GridError('All of (`X`, `Y`, `Z`) must share the same '
                                'two-dimensional size')
            else:
                if hdr is None:
                    hdr = {'xllcorner' : X[-1,0], 'yllcorner' : Y[-1,0]}
                    if Z.ndim == 2:
                        hdr['nbands'] = 1
                    elif Z.ndim == 3:
                        hdr['nbands'] = Z.shape[2]
                    else:
                        raise GridError('`Z` must be of dimension 2 or 3')
                    X -= X[-1,0]
                    Y -= Y[-1,0]
                self.X = X
                self.Y = Y
                self.Z = Z
        else:
            if True in (a is None for a in (X,Y,Z)):
                raise GridError('Either all or none of (`X`, `Y`, `Z`) must '
                                'be provided')
        self.set_hdr(hdr)
        return

    def _check_hdr(self, hdr):
        """ Check that the header contains the required fields. """
        for key in ('xllcorner', 'yllcorner', 'nbands'):
            if key not in hdr:
                raise GridError('Header missing {0}'.format(key))

    def rotate(self, deg, origin=(0.0, 0.0)):
        """ Rotate grid by *deg* degrees counter-clockwise around *origin*. """
        return


    def resample(self, X, Y):
        """ Resample internal grid to the points defined by `X`, `Y`. """
        raise NotImplementedError

    def fill_sinks(self):
        """ Fill depressions. Use the algorithm of Wang and Liu (2006). """
        return StructuredGrid(copy.copy(self._hdr),
                              X=self.X.copy(), Y=self.Y.copy(),
                              Z=fill_sinks(self.data))


class GridError(Exception):
    pass

class GridIOError(GridError):
    pass

def dummy_hdr(arr):
    if len(arr.shape) > 2:
        nbands = arr.shape[2]
    else:
        nbands = 1
    hdr = {'xllcorner': 0.0, 'yllcorner': 0.0,
           'nx': arr.shape[1], 'ny': arr.shape[0],
           'dx': 1.0, 'dy': 1.0,
           'nbands': nbands}
    return hdr


def readtif(incoming, band=0):
    """ Read a TIF image. If the image is contains bands, return band 0. """
    with tiffile.TiffFile(incoming) as tif:
        imdata = tif[0].asarray()
    rgrid = RegularGrid(dummy_hdr(imdata), Z=imdata)
    return rgrid


def readtifbands(incoming):
    """ Read a TIF image, returning a tuple of image data. """
    with tiffile.TiffFile(incoming) as tif:
        imdata = [page.asarray() for page in tif]
    rgridlist = [RegularGrid(dummy_hdr(a), Z=a) for a in imdata]
    return tuple(rgridlist)

def aairead(fnm):
    Z, aschdr = _aai.aairead(fnm)
    hdr = {'xllcorner'  : aschdr['xllcorner'],
           'yllcorner'  : aschdr['yllcorner'],
           'nx'         : aschdr['ncols'],
           'ny'         : aschdr['nrows'],
           'dx'         : aschdr['cellsize'],
           'dy'         : aschdr['cellsize'],
           'nbands'     : 1}
    Z[Z==aschdr['nodata_value']] = np.nan
    return RegularGrid(hdr, Z=Z)
