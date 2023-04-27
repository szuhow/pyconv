import sys
import os
import subprocess
import yaml
import logging
from yaml.loader import SafeLoader
from pathlib import Path
import optparse
import glob


class Oiiotool:
    def __init__(self, path):
        self.p = path


def bit(key) -> str:
    bits = {
      "8": "uint8",
      "16": "uint16",
      "32": "uint32",
    }
    return bits[key]


def check_path(file_path):
    dire = Path(str(file_path))
    if dire.is_dir():
        ex = True
    else:
        ex = False
    return ex


def get_conversion_path(data):
    try:
        path = data['img']['path']
    except KeyError:
        path = None
    return path


def validate_oiiotool(data):
    if not check_path(data['oiiotool']['path']):
        logging.warning("Invalid path for oiiotool")
        return
    ociocheck_path = data['oiiotool']['path']
    if ociocheck_path.endswith('/'):
        endpoint = "oiiotool"
    else:
        endpoint = "/oiiotool"
    path = ociocheck_path + endpoint
    output = subprocess.check_output([path], shell=True, stderr=subprocess.PIPE)
    result = output.decode("ascii", errors="ignore")
    for line in result.splitlines():
        if line == "oiiotool -- simple image processing operations":
            logging.info('Oiiotool load complete')
            o = Oiiotool(ociocheck_path)
            return o


def logger_config():
    log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # fileHandler = logging.FileHandler("{0}/{1}.log".format(logPath, fileName))
    file_handler = logging.FileHandler("logger.log")
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)


def get_args(argv):
    parser = optparse.OptionParser()
    # parser.add_option('-n', dest='num',
    #                   type='int',
    #                   help='specify the n''th table number to output')
    # parser.add_option('-o', dest='out',
    #                   type='string',
    #                   help='specify an output file (Optional)')
    parser.add_option("-p", "--path",
                      dest="path",
                      default=os.getcwd(),
                      help="Get path")
    (options, args) = parser.parse_args()
    if options.path:
        data, o = read_config_file(options.path)
        return data, o


def read_config_file(file_path):
    path_list = list()
    path = ''
    for path in Path(file_path).rglob('*.config'):
        path_list.append(path)
    if len(path_list) == 0:
        logging.warning('Config file missing')
    else:
        logging.info('Found config file')

        with open(path.name) as f:
            data = yaml.load(f, Loader=SafeLoader)
            o = validate_oiiotool(data)
            return data, o


def tokenize():
    pass


def search_files(dir_path, extension):
    for filename in glob.iglob(dir_path + '/*' + extension, recursive=True):
        if os.path.isfile(filename):
            return filename


def get_colorspace():
    pass


def convert(conv, path, o):
    try:
        in_colorspace = conv["input"]["colorspace"][0].lower().strip()
    except KeyError:
        in_colorspace = None
    out_ext = list()
    out_params = dict()
    cs = ["Color space:", "color_space:", "ColorSpace:"]
    for output_extension in conv["output"]["ext"]:
        out_ext.append(output_extension.split('/')[0])
        if len(output_extension.split('/')) > 1:
            out_params[output_extension.split('/')[0]] = output_extension.split('/')[1]

    for in_ext in conv["input"]["ext"]:
        filename = search_files(path, "." + in_ext.split('/')[0])
        if filename:
            output_info = subprocess.check_output([o.p + "/iinfo", filename, "-v"])
            result = output_info.decode("ascii", errors="ignore")

            if len(in_ext.split('/')) > 1:
                if in_ext.split('/')[1] in ("scanline", "tiled"):
                    in_params = in_ext.split('/')[1]
                else:
                    in_param = None

            try:
                file_colorspace = None
                for line in result.splitlines():
                    if any(x in line for x in cs):
                        file_colorspace = line.split(":")[2].replace('"', '').lower().strip()

                if in_colorspace is not None:
                    if in_colorspace == file_colorspace:
                        if in_ext.split('/')[0] in result.splitlines()[0]:
                            if len(in_ext.split('/')) > 1:
                                if bit(in_ext.split('/')[1]) not in result.splitlines()[0]:
                                    logging.info(f"Not found file with given params")
                                    return
                                else:
                                    logging.info(f"Found file: {filename} with given colorspace {file_colorspace} "
                                                 f"and depth {bit(in_ext.split('/')[1])}")
                            else:
                                logging.info(f"Found file: {filename} with given colorspace {file_colorspace}")
                else:

                    if len(in_ext.split('/')) > 1:
                        if bit(in_ext.split('/')[1]) not in result:
                            logging.info(f"Not found file with given params")
                            return

                        if in_ext.split('/')[0] in result:
                            logging.info(f"Found file: {filename}")
                    else:
                        if in_ext.split('/')[0] in result.splitlines()[0]:
                            logging.info(f"Found file: {filename}")


            except KeyError:
                logging.error("Not found depth value")


def conversion(d: dict, action: str, path, o):
    # tokenize(d)
    if not check_path(path):
        logging.warning("Missing path in config file. Conversion in current directory.")
        path = os.getcwd()
    else:
        logging.info('Found conversion path in config file.')
    for (k, v) in d[action].items():
        convert(v, path, o)


def main(argv):
    logger_config()
    data, o = get_args(argv)
    path = get_conversion_path(data)
    conversion(data, 'conversions', path, o)


if __name__ == '__main__':
    main(sys.argv[1:])

