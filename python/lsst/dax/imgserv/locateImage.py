# This file is part of dax_imgserv.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (http://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This module is used to locate and retrieve various images
(e.g. raw, calexp, deepCoadd), and their related metadata.

@author: John Gates, SLAC
@author: Brian Van Klaveren, SLAC
@author: Kenny Lo, SLAC

"""

import lsst.log as log
import lsst.afw.image as afw_image

from .getimage.imageget import ImageGetter
from .butlerGet import ButlerGet
from .metaservGet import MetaservGet
from .dispatch import Dispatcher


def image_open(W13db, config, logger=log):
    """Open access to specified images (raw, calexp, deepCoadd,etc) of
    specified image repository.

    Returns
    -------
    imagegetter : obj
        instance for access to all image operations.

    """
    imagedb = W13db(config, logger)
    return ImageGetter(imagedb.butlerget, imagedb.metaservget, logger)


def get_image(params, config) -> afw_image:
    """Get the image per query request synchronously (default).

    Parameters
    ----------
    params : `dict`
        the request parameters.
    config : `dict`
        the config file.

    Returns
    -------
    image : afw_image
        the requested image if found.

    """
    dispatcher = Dispatcher(config["DAX_IMG_CONFIG"])
    api, api_params = dispatcher.find_api(params)
    config["DAX_IMG_META_DB"] = api_params.get("db", None)
    ds = api_params.get("ds", None)
    if ds is None:
        raise Exception("Missing ds parameter")
    w13db = get_ds(ds.strip())
    img_getter = image_open(w13db, config)
    if img_getter is None:
        raise Exception("Failed to instantiate ImageGetter")
    image = api(img_getter, api_params)
    return image


def get_ds(image_type):
    """ Get the database corresponding to the image type.

    Parameters
    ----------
    image_type: `str`
        the image type.

    Returns
    -------
    ds : 'w13Db`
        the database object, if found.

    """
    it = image_type.lower()
    if it == "raw":
        return W13RawDb
    elif it == "calexp":
        return W13CalexpDb
    elif it == "deepcoadd":
        return W13DeepCoaddDb
    else:
        raise Exception("Invalid ds parameter")


class W13Db:
    """This is the base class for examining DC_W13_Stripe82 image data,
    Thie instantates a Butler for access to image repository, as well as
    connection for metadata via MetaServ.

    Attributes
    ----------
    imagegetter : obj
        To be used for accessing images.
    """

    def __init__(self, config, table, columns, dataRoot,
            butlerPolicy, butlerKeys, logger):
        """Instantiate W13Db object with credential for database, butler
        configuration, and logger.

        Parameters
        ----------
        config: Dict
            configuration file for this imgserv instance.
        table : str
            The table name.
        columns : str
            The database columns.
        dataRoot : str
            root for the butler.
        butlerPolicy : str
            The butler policy.
        butlerKeys : str
                     The butler keys for this image data source.
        logger : obj
            The logger to be used.

        """
        self.butlerget = ButlerGet(dataRoot, butlerPolicy, butlerKeys, logger)
        self.metaservget = MetaservGet(
                config["dax.imgserv.meta.url"],
                config["DAX_IMG_META_DB"],
                table, columns, logger)


class W13RawDb(W13Db):
    """This class is used to connect to the DC_W13_Stripe82 Raw database.
    Raw images
    ----------
    Repository path: /datasets/sdss/preprocessed/dr7/runs
    Butler keys: run, camcol, field, filter
    MySQL table: DC_W13_Stripe82.Science_Ccd_Exposure
    Table columns: run, camcol, field, filterName
    butler.get("raw", run=run, camcol=camcol, field=field, filter=filterName)

    """
    def __init__(self, config, logger=log):
        """Instantiate W13RawDb object with DB credential info and logger."""
        W13Db.__init__(self,
                       config,
                       table=config["DAX_IMG_TAB_SCICCDEXP"],
                       columns=config["DAX_IMG_COLUMNS1"],
                       dataRoot=config["DAX_IMG_DR"],
                       butlerPolicy=config["DAX_IMG_BUTLER_POL0"],
                       butlerKeys=config["DAX_IMG_BUTLER_KEYS1"],
                       logger=logger)


class W13CalexpDb(W13RawDb):
    """This class is used to connect to the DC_W13_Stripe82 Calibration Exposures.
    Calibration Exposures look to be very similar to retrieving Raw exposres. Once
    this is shown to work, W13CalebDb and W13RawDb should be refactored to have a
    commnon base class and add a field for policy "fpC" or "calexp".
    ----------
    Repository path: /datasets/sdss/preprocessed/dr7/sdss_stripe82_00/calexps/
    Butler keys: run, camcol, field, filter
    MySQL table: DC_W13_Stripe82.Science_Ccd_Exposure
    Table columns: run, camcol, field, filterName
    butler.get("calexp", run=run, camcol=camcol, field=field, filter=filterName)

    """
    def __init__(self, config, logger=log):
        """Instantiate W13CalexpDb object with DB credential info and
        logger."""
        W13Db.__init__(self,
                       config,
                       table=config["DAX_IMG_TAB_SCICCDEXP"],
                       columns=config["DAX_IMG_COLUMNS1"],
                       dataRoot=config["DAX_IMG_DS"]+"/calexps",
                       butlerPolicy=config["DAX_IMG_BUTLER_POL1"],
                       butlerKeys=config["DAX_IMG_BUTLER_KEYS1"],
                       logger=logger)


class W13DeepCoaddDb(W13Db):
    """This class is used to connect to the DC_W13_Stripe82 Coadd database.
    Coadd images
    ------------
    Repository path: "/datasets/sdss/preprocessed/dr7/sdss_stripe82_00/coadd"
    Butler keys: tract, patch, filter
    MySQL table: DC_W13_Stripe82.DeepCoadd
    Table columns: tract, patch, filterName
    butler.get("deepCoadd", filter=filterName, tract=tract, patch=patch)

    """
    def __init__(self, config, logger=log):
        """Instantiate W13DeepCoaddDb object with DB credential and logger."""
        W13Db.__init__(self,
                       config,
                       table=config["DAX_IMG_TAB_DEEPCOADD"],
                       columns=config["DAX_IMG_COLUMNS2"],
                       dataRoot=config["DAX_IMG_DS"]+"/coadd",
                       butlerPolicy=config["DAX_IMG_BUTLER_POL2"],
                       butlerKeys=config["DAX_IMG_BUTLER_KEYS2"],
                       logger=logger)


