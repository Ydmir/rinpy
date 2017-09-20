import numpy as np
import re
import datetime
import struct


class RinexError(Exception):
    pass


def getrinexversion(filename):
    """ Scan the file for RINEX version number.

    Parameters
    ---------
    filename : str
        Filename of the rinex file

    Returns
    -------
    version : str
        Version number.
    """
    with open(filename, 'r') as f:
        line = f.readline()
        while 'RINEX VERSION / TYPE' not in line:
            line = f.readline()

            if 'END OF HEADER' in line:
                raise RinexError("No 'RINEX VERSION / TYPE' found.")
    return line[:9].strip()


def readheader(lines, rinexversion):
    """ Read and return header information for the RINEX file

    Parameters
    ----------
    lines : list[str]
        List of each line in the RINEX file.

    Returns
    -------
    header : dict
        Dict containing the header information from the RINEX file.

    headerlines : list[int]
        List of starting line for the headers of each data block.

    headerlengths : list[int]
        List of length for the headers of each data block.

    obstimes : list[datetime.datetime]
        List of time of measurement for each measurement epoch.

    satlists : list[list[str]]
        List containing lists of satellites present in each block.

    satset : set(str)
        Set containing all satellites in the data.
    """
    try:
        if '2.1' in rinexversion:
            return _readheader_v21(lines)
        else:
            raise RinexError('RINEX v%s is not supported.' % rinexversion)

    except KeyError as e:
        raise RinexError('Missing required header %s' % str(e))


def _readheader_v21(lines):
    """ Read rinex version 2.10 and 2.11 """

    header = {}
    # Capture header info

    for i, line in enumerate(lines):
        if "END OF HEADER" in line:
            i += 1  # skip to data
            break

        if line[60:80].strip() not in header:  # Header label
            header[line[60:80].strip()] = line[:60]  # don't strip for fixed-width parsers
            # string with info
        else:
            header[line[60:80].strip()] += " "+line[:60]
            # concatenate to the existing string

    header['# / TYPES OF OBSERV'] = header['# / TYPES OF OBSERV'].split()
    # The first number is the integer number of observations:
    header['# / TYPES OF OBSERV'][0] = int(header['# / TYPES OF OBSERV'][0])
    rowpersat = 1 + header['# / TYPES OF OBSERV'][0] // 5

    header['RINEX VERSION / TYPE'] = header['RINEX VERSION / TYPE'][:9].strip()
    header['APPROX POSITION XYZ'] = [float(coord) for coord in header['APPROX POSITION XYZ'].split()]

    header['TIME OF FIRST OBS'] = [part for part in header['TIME OF FIRST OBS'].split()]

    if 'INTERVAL' in header:
        header['INTERVAL'] = float(header['INTERVAL'][:10])

    if '# OF SATELLITES' in header:
        header['# OF SATELLITES'] = int(header['# OF SATELLITES'][:6])

    headerlines = []
    headerlengths = []
    obstimes = []
    satlists = []
    satset = set()

    century = int(header['TIME OF FIRST OBS'][0][:2]+'00')
    # This will result in an error if the record overlaps the end of the century. So if someone feels this is a major
    # problem, feel free to fix it. Personally can't bother to do it...

    pattern = re.compile('(\s{2}\d{1}|\s{1}\d{2}){2}')

    while i < len(lines):
        if pattern.match(lines[i][:6]):  # then it's the first line in a header record
            if int(lines[i][28]) in (0, 1, 6):  # CHECK EPOCH FLAG  STATUS
                headerlines.append(i)
                year, month, day, hour = lines[i][1:3], lines[i][4:6], lines[i][7:9], lines[i][10:12]
                minute, second = lines[i][13:15], lines[i][16:26]
                obstimes.append(datetime.datetime(year=century+int(year),
                                                  month=int(month),
                                                  day=int(day),
                                                  hour=int(hour),
                                                  minute=int(minute),
                                                  second=int(float(second)),
                                                  microsecond=int(float(second) % 1 * 100000)))

                numsats = int(lines[i][29:32])  # Number of visible satellites %i3
                headerlengths.append(1 + (numsats-1)//12)  # number of lines in header, depends on how many svs on view

                if numsats > 12:
                    sv = []
                    for s in range(numsats):
                        if s > 0 and s % 12 == 0:
                            i += 1
                        sv.append(lines[i][32+(s%12)*3:35+(s%12)*3])
                    satlists.append(sv)

                else:
                    satlists.append([lines[i][32+s*3:35+s*3] for s in range(numsats)])

                i += numsats*rowpersat+1

            else:  # there was a comment or some header info
                flag = int(lines[i][28])
                if(flag != 4):
                    print(flag)
                skip = int(lines[i][30:32])
                i += skip+1
        else:
            # We have screwed something up and have to iterate to get to the next header row, or eventually the end.
            i += 1

    for satlist in satlists:
        satset = satset.union(satlist)

    return header, headerlines, headerlengths, obstimes, satlists, satset


def _converttofloat(numberstr):
    try:
        return float(numberstr)
    except ValueError:
        return np.nan


def _readblocks_v21(lines, header, headerlines, headerlengths, satlists, satset):
    """ Read the lines of data.

    Parameters
    ----------
    lines : list[str]
        List of each line in the RINEX file.

    header : dict
        Dict containing the header information from the RINEX file.
        
    headerlines : list[int]
        List of starting line for the headers of each data block.

    headerlengths : list[int]
        List of length for the headers of each data block.

    satlists : list[list[str]]
        List containing lists of satellites present in each block.

    satset : set(str)
        Set containing all satellites in the data.

    Returns
    -------
    systemdata : dict
        Dict with data-arrays.

    systemsatlists : dict
        Dict with lists of visible satellites.

    prntoidx : dict
        Dict with translation dicts.

    obstypes : dict
        Dict with observation types.

    See also
    --------
    processrinexfile : The wrapper.
    """
    nobstypes = header['# / TYPES OF OBSERV'][0]
    rowpersat = 1 + header['# / TYPES OF OBSERV'][0] // 5
    nepochs = len(headerlines)

    systemletters = set([letter for letter in set(''.join(satset)) if letter.isalpha()])
    systemsatlists = {letter: [] for letter in systemletters}

    systemdata = {}
    prntoidx = {}
    obstypes = {}

    for sat in satset:
        systemsatlists[sat[0]].append(int(sat[1:]))

    for letter in systemletters:
        systemsatlists[letter].sort()
        nsats = len(systemsatlists[letter])
        systemdata[letter] = np.nan * np.zeros((nepochs, nsats, nobstypes))
        prntoidx[letter] = {prn: idx for idx, prn in enumerate(systemsatlists[letter])}
        obstypes[letter] = header['# / TYPES OF OBSERV'][1:]  # Proofing for V3 functionality

    colwidths=(14, 1, 1)*nobstypes
    fmt = '14s 2x '*nobstypes
    fieldstruct = struct.Struct(fmt)
    parse = fieldstruct.unpack_from

    for iepoch, (headerstart, headerlength, satlist) in enumerate(zip(headerlines, headerlengths, satlists)):
        for i, sat in enumerate(satlist):
            datastring = ''.join(["{:<80}".format(line.rstrip()) for line in lines[headerstart+headerlength+rowpersat*i:headerstart+headerlength+rowpersat*(i+1)]])
            data = np.array([_converttofloat(number.decode('ascii')) for number in parse(datastring.encode('ascii'))])

            systemletter = sat[0]
            prn = int(sat[1:])

            systemdata[systemletter][iepoch, prntoidx[systemletter][prn], :] = data

    return systemdata, systemsatlists, prntoidx, obstypes


def processrinexfile(filename, savefile=None):
    """ Process a RINEX file into python format

    Parameters
    ----------
    filename : str
        Filename of the rinex file

    Returns
    -------
    systemdata : dict
        Dict with a nobs x nsats x nobstypes nd-array for each satellite constellation containing the measurements. The
        keys of the dict correspond to the systemletter as used in RINEX files (G for GPS, R for GLONASS, etc).

        nobs is the number of observations in the RINEX data, nsats the number of visible satellites for the particular
        system during the whole measurement period, and nobstypes is the number of different properties recorded.

    systemsatlists : dict
        Dict containing the full list of visible satellites during the whole measurement period for each satellite
        constellation.

    prntoidx : dict
        Dict which for each constellation contains a dict which translates the PRN number into the index of the
        satellite in the systemdata array.

    obstypes : dict
        Dict containing the observables recorded for each satellite constellation.

    header : dict
        Dict containing the header information from the RINEX file.

    obstimes : list[datetime.datetime]
        List of time of measurement for each measurement epoch.
    """
    rinexversion = getrinexversion(filename)

    with open(filename, 'r') as f:
        lines = f.read().splitlines(True)

    try:
        if '2.1' in rinexversion:
            header, headerlines, headerlengths, obstimes, satlists, satset = _readheader_v21(lines)
        else:
            raise RinexError('RINEX v%s is not supported.' % rinexversion)
    except KeyError as e:
        raise RinexError('Missing required header %s' % str(e))

    if '2.1' in rinexversion:
        systemdata, systemsatlists, prntoidx, obstypes = _readblocks_v21(lines, header,
                                                                         headerlines, headerlengths,
                                                                         satlists, satset)

    if savefile is not None:
        saverinextonpz(savefile, systemdata, systemsatlists, prntoidx, obstypes, header, obstimes)

    return systemdata, systemsatlists, prntoidx, obstypes, header, obstimes


def saverinextonpz(savefile, systemdata, systemsatlists, prntoidx, obstypes, header, obstimes):
    """ Save data to numpy's npz format.

    Parameters
    ----------
    savefile : str
        Path to where to save the data.

    systemdata, systemsatlists, prntoidx, obstypes, header, obstimes: dict
        Data as returned from processrinexfile

    See Also
    --------
    processrinexfile
    """
    savestruct = {}
    savestruct['systems'] = []

    for systemletter in systemdata:
        savestruct[systemletter+'systemdata'] = systemdata[systemletter]
        savestruct[systemletter+'systemsatlists'] = systemsatlists[systemletter]
        savestruct[systemletter+'prntoidx'] = prntoidx[systemletter]
        savestruct[systemletter+'obstypes'] = obstypes[systemletter]
        savestruct['systems'].append(systemletter)

    savestruct['obstimes'] = obstimes
    savestruct['header'] = header

    np.savez_compressed(savefile, **savestruct)


def loadrinexfromnpz(npzfile):
    """ Load data previously stored in npz-format

    Parameters
    ----------
    npzfile : str
        Path to the stored data.

    Returns
    -------
    systemdata, systemsatlists, prntoidx, obstypes, header, obstimes: dict
        Data in the same format as returned by processrinexfile
    """
    rawdata = np.load(npzfile)

    systemdata = {}
    systemsatlists = {}
    prntoidx = {}
    obstypes = {}

    for systemletter in rawdata['systems']:
        systemdata[systemletter] = rawdata[systemletter+'systemdata']
        systemsatlists[systemletter] = list(rawdata[systemletter+'systemsatlists'])
        prntoidx[systemletter] = rawdata[systemletter+'prntoidx'].item()
        obstypes[systemletter] = list(rawdata[systemletter+'obstypes'])

    header = rawdata['header'].item()
    obstimes = list(rawdata['obstimes'])

    return systemdata, systemsatlists, prntoidx, obstypes, header, obstimes
