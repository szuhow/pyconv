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
        path = data["img"]["path"]
    except KeyError:
        path = None
    return path


def validate_oiiotool(data):
    if not check_path(data["oiiotool"]["path"]):
        logging.warning("Invalid path for oiiotool")
        return
    ociocheck_path = data["oiiotool"]["path"]
    if ociocheck_path.endswith("/"):
        endpoint = "oiiotool"
    else:
        endpoint = "/oiiotool"
    path = ociocheck_path + endpoint
    output = subprocess.check_output([path], shell=True, stderr=subprocess.PIPE)
    result = output.decode("ascii", errors="ignore")
    for line in result.splitlines():
        if line == "oiiotool -- simple image processing operations":
            logging.info("Oiiotool load complete")
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
    parser.add_option("-p", "--path", dest="path", default=os.getcwd(), help="Get path")
    (options, args) = parser.parse_args()
    if options.path:
        data, o = read_config_file(options.path)
        return data, o


def read_config_file(file_path):
    path_list = list()
    path = ""
    for path in Path(file_path).rglob("*.config"):
        path_list.append(path)
    if len(path_list) == 0:
        logging.warning("Config file missing")
    else:
        logging.info("Found config file")

        with open(path.name) as f:
            data = yaml.load(f, Loader=SafeLoader)
            o = validate_oiiotool(data)
            return data, o


def tokenize(data):
    if data["tokenize"]["with"]:
        return True
    else:
        return False


def filext(a: str):
    out = a.split(".")
    return out[1]


def recursive_glob(path, ext):
    return [
        os.path.join(looproot, filename)
        for looproot, _, filenames in os.walk(path)
        for filename in filenames
        if filename.endswith(ext)
    ]


def recursive_glob_extless(path):
    return [
        os.path.join(looproot, filename)
        for looproot, _, filenames in os.walk(path)
        for filename in filenames
    ]


def convert(conv, path, o, data):
    out_ext = list()
    out_params = dict()
    try:
        in_colorspace = conv["input"]["colorspace"][0].lower().strip()
    except KeyError:
        in_colorspace = None
    try:
        out_colorspace = conv["output"]["colorspace"][0].lower().strip()
    except KeyError:
        out_colorspace = None
    for output_extension in conv["output"]["ext"]:
        out_ext.append(output_extension.split("/")[0])
        if len(output_extension.split("/")) > 1:
            out_params[output_extension.split("/")[0]] = output_extension.split("/")[1]
    for in_ext in conv["input"]["ext"]:
        file = recursive_glob(path, "." + in_ext.split("/")[0])
        if file:
            for filename in file:
                output_info = subprocess.check_output([o.p + "/iinfo", filename, "-v"])
                result = output_info.decode("ascii", errors="ignore")
                if tokenize(data):
                    if data["tokenize"]["with"][0] in filename:
                        inc = data["tokenize"]["action"]["input"]["colorspace"]
                        outc = data["tokenize"]["action"]["output"]["colorspace"]
                        if inc:
                            in_colorspace = inc[0]
                        if outc:
                            out_colorspace = outc[0]
                if len(in_ext.split("/")) > 1:
                    if in_ext.split("/")[1] in ("scanline", "tiled"):
                        in_params = in_ext.split("/")[1]
                    else:
                        in_param = None
                try:
                    if in_ext.split("/")[0] in result.splitlines()[0]:
                        if len(in_ext.split("/")) > 1:
                            if bit(in_ext.split("/")[1]) not in result.splitlines()[0]:
                                # logging.info(f"Not found file with given params")
                                return
                            else:

                                subprocess.run(
                                    [
                                        o.p + "/oiiotool",
                                        filename,
                                        "--colorconvert",
                                        in_colorspace,
                                        out_colorspace,
                                        "-o",
                                        filename.replace("." + filext(filename), "")
                                        + "_export_."
                                        + out_ext[0],
                                    ]
                                )
                                subprocess.run(
                                    [
                                        "chmod",
                                        "go-w",
                                        filename.replace("." + filext(filename), "")
                                        + "_export_."
                                        + out_ext[0],
                                    ]
                                )
                                logging.info(
                                    f"Found file: {filename} with given depth {bit(in_ext.split('/')[1])} and converting from {in_colorspace} to {out_colorspace} as write-protected"
                                )
                        else:

                            subprocess.run(
                                [
                                    o.p + "/oiiotool",
                                    filename,
                                    "--colorconvert",
                                    in_colorspace,
                                    out_colorspace,
                                    "-o",
                                    filename.replace("." + filext(filename), "")
                                    + "_export_."
                                    + out_ext[0],
                                ]
                            )
                            subprocess.run(
                                [
                                    "chmod",
                                    "go-w",
                                    filename.replace("." + filext(filename), "")
                                    + "_export_."
                                    + out_ext[0],
                                ]
                            )
                            logging.info(
                                f"Found file: {filename} and converting from {in_colorspace} to {out_colorspace} as write-protected"
                            )

                except KeyError:
                    pass
                    # logging.error("Not found depth value")


def safeget(d, *keys):
    for key in keys:
        try:
            d = d[key]
        except KeyError:
            return None
    return d


def proxy(data: dict, action: str, path, o):
    try:
        if safeget(data, 'proxy', 'in', 'max_size') and safeget(data, 'proxy', 'out', 'ext') and safeget(data, 'proxy', 'out', 'max_size'):
            max_in_size = int(safeget(data, 'proxy', 'in', 'max_size'))
            max_out_size = int(safeget(data, 'proxy', 'out', 'max_size'))
            out_ext = safeget(data, 'proxy', 'out', 'ext')
        else:
            return
    except ValueError:
        logging.error("Size values must be integers")
        return
    exts = ("jpg", "tiff", "tif", "dpx")
    file = recursive_glob(path, exts)
    if file:
        for filename in file:
            output_info = subprocess.check_output([o.p + "/iinfo", filename, "-v"])
            result = output_info.decode("ascii", errors="ignore")
            res = result.splitlines()[0].split(':')[1].split(',')[0].replace(" ", "").split('x')
            if any(int(num) > max_in_size for num in res):
                x, y = 0
                if int(res[0]) > max_in_size:
                    x = max_out_size
                    y = 0
                elif int(res[1]) > max_in_size:
                    x = 0
                    y = max_out_size
                subprocess.run(
                    [
                        o.p + "/oiiotool",
                        filename,
                        "--resize",
                        'x'.join(map(str, (x,y))),
                        "-o",
                        filename.replace("." + filext(filename), "")
                        + "_proxy_."
                        + out_ext,
                    ]
                )





def conversion(data: dict, action: str, path, o):
    if not check_path(path):
        logging.warning("Missing path in config file. Conversion in current directory.")
        path = os.getcwd()
    else:
        logging.info("Found conversion path in config file.")
    for k, v in data[action].items():
        convert(v, path, o, data)


def main(argv):
    logger_config()
    data, o = get_args(argv)
    path = get_conversion_path(data)
    # conversion(data, "conversions", path, o)
    proxy(data, "proxy", path, o)


if __name__ == "__main__":
    main(sys.argv[1:])
