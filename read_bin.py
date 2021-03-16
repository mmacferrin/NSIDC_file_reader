# -*- coding: utf-8 -*-
"""
Created on Fri Feb 21 15:03:50 2020

@author: mmacferrin
"""
import numpy
import argparse
import re
import os

# 332 rows x 316 cols for Antarctic Polar Stereo data,
# per https://nsidc.org/data/polar-stereo/ps_grids.html
#
# If you are using Arctic data or some other grid, change the DEFAULT_GRID_SHAPE below,
# or just use the optional parameter when you call it.
# For Antarctica, (rows, cols) = (332,316)
# For Arctic, (rows, cols) = (448, 304)
DEFAULT_GRID_SHAPE = (332, 316)

GRIDSIZE_25_N = numpy.array(((5850+5350)/25, (3750+3850)/25), dtype=numpy.long) # (448, 304)
GRIDSIZE_25_S = numpy.array(((4350+3950)/25, (3950+3950)/25), dtype=numpy.long) # (332, 316)
GRIDSIZE_12_5_N = GRIDSIZE_25_N * 2 # (896, 608)
GRIDSIZE_12_5_S = GRIDSIZE_25_S * 2 # (664, 632)
GRIDSIZE_6_25_N = GRIDSIZE_25_N * 4
GRIDSIZE_6_25_S = GRIDSIZE_25_S * 4


def read_NSIDC_bin_file(fname,
                        grid_shape = DEFAULT_GRID_SHAPE,
                        header_size=0,
                        element_size=2,
                        return_type=float,
                        signed=False,
                        multiplier=0.1):
    """Read an SSMI file, return a 2D grid of integer values.

    header_size - size, in bytes, of the header. Defaults to zero for
        brightness-temperature data, but can be one for other data. For instance,
        NSIDC sea-ice concentration data has a 300-byte header on it.

    element_size - number of bytes for each numerical element. The brightness-temperature
        uses 2-byte little-endian integers (with a multiplier factor to turn them into floating-point values).
        NSIDC sea-ice concentration data is just 1-byte integers.

    return_type can be "int" or "float", or the numpy equivalent therein.

    signed - Whether the data values are signed (True) or unsigned (False) data

    multiplier -- A value to multiply the dataset by after it's read. Ingored for integer arrays,
        useful in some cases for floating point values that are saved as integers but then
        multiplied by 0.1 to get floating-point values.
        (Example: value "2731" with a multiplier of 0.1 will return 273.1)
        This is ingored if the return type is "int" or a numpy integer type.
    """
    # Data is in two-byte, little-endian integers, array of size GRID_SHAPE
    with open(fname, 'rb') as fin:
        raw_data = fin.read()
        fin.close()

    # Lop off the header from the start of the byte array.
    if header_size > 0:
        raw_data = raw_data[header_size:]

    # Check to make sure the data is the right size, raise ValueError if not.
    # TODO: The NSIDC-0051 data has the rows,cols in the header. We could read it from there,
    # although right now we just get the grid size from the paramter.
    if int(len(raw_data) / element_size) != int(numpy.product(grid_shape)):
        raise ValueError("File {0} has {1} elements, does not match grid size {2}.".format(
                         fname, int(len(raw_data)/element_size), str(grid_shape)))

    # Creating a uint16 array to read the data in
    int_array = numpy.empty(grid_shape, dtype=return_type)
    int_array = int_array.flatten()

    # Read the data. The built_int "from_bytes" function does the work here.
    for i in range(0, int(len(raw_data)/element_size)):
        int_array[i] = int.from_bytes(raw_data[(i*element_size):((i+1)*element_size)],
                                      byteorder="little",
                                      signed=signed)

    # Unflatten the array back into the grid shape
    int_array.shape = grid_shape

    # If the file is meant to be an integer array, just return it.
    if return_type in (int, numpy.int, numpy.uint8, numpy.int8, numpy.uint16, numpy.int16, numpy.uint32, numpy.int32, numpy.uint64, numpy.int64):
        return_array = numpy.array(int_array, dtype=return_type)
    # Else, if it's meant to be a floating-point array, scale by the multiplier
    # and return the floating-point array. If the mutiplier is a float (i.e. 0.1),
    # numpy will conver and return an array of floats
    else:
        return_array = numpy.array( int_array * multiplier, dtype=return_type)

    return return_array

def get_hemisphere_and_resolution_from_nsidc_filename(fname):
    """Get the resolution from the filename.

    From the file specs on https://nsidc.org/data/nsidc-0001
    Will be 12.5 or 25 km.
    """
    fbase = os.path.splitext(os.path.split(fname)[1])[0]

    # This is the filename structure for NSIDC-0001. TODO: Generalize it for other file name structures.
    SSMI_REGEX =  r"(?<=\Atb_f\d{2}_\d{8}_v\d_)[ns]\d{2}(?=[vh])"

    matches = re.search(fbase, SSMI_REGEX)
    if matches is None:
        return None, None

    match = matches.group(0)
    hemisphere = match[0].upper()

    frequency = int(match[1:2])

    # The resolutions for each frequency in the NSIDC data products.
    # Dictionary is "frequency:resolutin" key:value pair.
    resolution = {19:25.0,
                  22:25.0,
                  37:25.0,
                  85:12.5,
                  91:12.5}[frequency]

    return hemisphere, resolution

def output_array_to_stdout(array):
    """Output a 2D array to stdout."""
    for row in array:
        print(" ".join([str(i) for i in row]))
    return

def testing():
    """Just a few test functions."""
    # Testing this out on a few files, examples using different types of data products.

    # An NSIDC-0001 brightness-temperature file, in 2-byte little-endian integers
    # converted to floating point. No header.
    array1 = read_NSIDC_bin_file("../Tb/nsidc-0001/tb_f08_19870709_v5_s19h.bin",
                                 grid_shape=(332,316),
                                 header_size=0,
                                 element_size=2,
                                 return_type=float,
                                 signed=False,
                                 multiplier=0.1)

    print(array1.shape, array1.dtype)
    print(array1)

    # An NSIDC-0051 sea-ice concentration v1 file, in a 1-byte unsigned integer array with
    # a 300-byte header.

    # For an Arctic file
    array2 = read_NSIDC_bin_file("../Tb/nsidc-0051/nt_20201231_f17_v1.1_n.bin",
                                 grid_shape=(448, 304),
                                 header_size=300,
                                 element_size=1,
                                 return_type=int,
                                 signed=False)

    print(array2.shape, array2.dtype)
    print(array2)

    # For an Antarctic file
    array3 = read_NSIDC_bin_file("../Tb/nsidc-0051/nt_20201231_f17_v1.1_s.bin",
                                 grid_shape=(332,316),
                                 header_size=300,
                                 element_size=1,
                                 return_type=int,
                                 signed=False)

    print(array3.shape, array3.dtype)
    print(array3)

    # An NSIDC-0079 sea-ice concentration v3 files, in 2-byte unsigned integer array with
    # a 300-byte header.

    # For an Arctic file, returning the array in integer values.
    array4 = read_NSIDC_bin_file("../Tb/nsidc-0079/bt_20201231_f17_v3.1_n.bin",
                                 grid_shape=(448, 304),
                                 header_size=0,
                                 element_size=2,
                                 return_type=int,
                                 signed=False)

    print(array4.shape, array4.dtype)
    print(array4)

    # For an Antarctic file, alternately returning the array in floating-point values (your choice, just pick the parameter you want.)
    array5 = read_NSIDC_bin_file("../Tb/nsidc-0079/bt_20201231_f17_v3.1_s.bin",
                                 grid_shape=(332,316),
                                 header_size=0,
                                 element_size=2,
                                 return_type=float,
                                 signed=False,
                                 multiplier=0.1)

    print(array5.shape, array5.dtype)
    print(array5)

def read_and_parse_args():
    """Read and parse command-line arguments."""
    parser = argparse.ArgumentParser(description="""Reads an NSIDC .bin file and outputs the array contents. Use
'convert_bin_to_gtif.py' to output to a GeoTiff. This will just spit the
numbers onto a screen. In order to output to a space-delimited text file, just
route the stdout into a file. Example:

                $ python read_bin.py infile.bin > outfile.txt

Read the NSIDC documentation for your data product in order to
choose the correct parameters listed below.""")
    parser.add_argument("src", type=str, help="Source file (.bin)")
    parser.add_argument("-resolution", "-r", type=float, default=None, help="Resolution (km): 6.25, 12.5, or 25. If omitted, it is interpreted from the file name. If cannot be interpreted, defaults to 25 km. Check your NSIDC data source documentation.")
    parser.add_argument("-hemisphere", type=str, default=None, help="Hemisphere: N or S. If omitted, it is interpreted from the file name. If cannot be interpreted, defaults to 'N'.")
    parser.add_argument("-header_size", "-hs", type=int, default=0, help="Size of .bin file header (in bytes.) (Default: 0)")
    parser.add_argument("-element_size", "-es", type=int, default=2, help="Size of each numerical .bin data element, in bytes. Most NSIDC files use 1- or 2-byte numbers. Check the documentation of the dataset. (Default: 2)")
    parser.add_argument("-output_type", "-ot", default="int", help="Output data type: 'int' or 'float'. Default 'int'.")
    parser.add_argument("-multiplier","-m", type=str, default="auto", help="A multiplier to create the output numbers. Any number, or 'auto'. With 'auto', defaults to 1 for integers (no modification) and 0.1 for floating-point (2731 becomes 273.1, e.g.). Or, specify your own multiplier here.")
    parser.add_argument("--signed", "-s", action="store_true", default=False, help="Read bin as signed data. Default to unsigned.")

    return parser.parse_args()

if __name__ == "__main__":
    # Parse the command-line arguments.
    args = read_and_parse_args()

    if args.output_type.lower() in ("float", "f"):
        out_type = float
    elif args.output_type.lower() in ("int", "i", "d"):
        out_type = int
    else:
        raise ValueError("Uknown output_type (can be: 'int','i','d','float', or 'f'):", str(args.output_type))

    if args.multiplier.lower().strip() != "auto":
        multiplier = float(args.multiplier)
    else:
        multiplier = args.multiplier

    # Resolve the resolution, from:
    # 1) The command line argument
    # 2) The filename, or
    # 3) Just use the default (25 km))
    if args.resolution is None or args.hemisphere is None:
        hemisphere_from_fname, resolution_from_fname = get_hemisphere_and_resolution_from_nsidc_filename(args.src)
    if args.resolution is None:
        if resolution_from_fname is None:
            resolution = 25
        else:
            resolution = resolution_from_fname
    else:
        resolution = float(args.resolution)

    if args.hemisphere is None:
        if hemisphere_from_fname is None:
            hemisphere = 'N'
        else:
            hemisphere = hemisphere_from_fname
    else:
        hemisphere = args.hemisphere.strip().upper()

    if hemisphere == 'N':
        if resolution == 25:
            gridsize = GRIDSIZE_25_N
        elif resolution == 12.5:
            gridsize = GRIDSIZE_12_5_N
        elif resolution == 6.25:
            gridsize = GRIDSIZE_6_25_N
        else:
            raise ValueError("Unknown resolution: {0}".format(resolution))

    elif hemisphere == 'S':
        if resolution == 25:
            gridsize = GRIDSIZE_25_S
        elif resolution == 12.5:
            gridsize = GRIDSIZE_12_5_S
        elif resolution == 6.25:
            gridsize = GRIDSIZE_6_25_S
        else:
            raise ValueError("Unknown resolution: {0}".format(resolution))

    else:
        raise ValueError("Unknown hemisphere: {0}".format(hemisphere))

    # Read the array
    array = read_NSIDC_bin_file(args.src,
                                grid_shape = gridsize,
                                header_size=args.header_size,
                                element_size=args.element_size,
                                return_type=out_type,
                                signed=args.signed,
                                multiplier=args.multiplier)

    # Print the array to stdout
    output_array_to_stdout(array)