import os
import sys
import argparse

already_wiped = False
def parse_sim_argv(argv=None, get_f=False):
    from core.runtime import set_runtime_opt
    from utils.errors import FileNotFoundError
    from core.product import PKG_D, ROOT_D
    global already_wiped
    prog = "mml run"
    desc = """{0}: run a matmodlab simulation script in the matmodlab
    environment. Simulation scripts can be run directly by the python
    interpreter if {1} is on your PYTHONPATH.""".format(prog, ROOT_D)
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(prog=prog, description=desc)
    parser.add_argument("-v", default=1, type=int,
       help="Verbosity [default: %(default)s]")
    parser.add_argument("--dbg", default=False, action="store_true",
       help="Debug mode [default: %(default)s]")
    parser.add_argument("--sqa", default=False, action="store_true",
       help="SQA mode [default: %(default)s]")
    parser.add_argument("--switch", metavar="MATERIAL",
       help="Switch material in input with MATERIAL [default: %(default)s]")
    parser.add_argument("--mimic", metavar="MATERIAL",
       help=("Set parameters of input material to mimic MATERIAL "
             "(not supported by all models) [default: %(default)s]"))
    parser.add_argument("-I", default=os.getcwd(), help=argparse.SUPPRESS)
    parser.add_argument("-B", metavar="MATERIAL",
        help="Wipe and rebuild MATERIAL before running [default: %(default)s]")
    parser.add_argument("-V", default=False, action="store_true",
        help="Launch results viewer on completion [default: %(default)s]")
    parser.add_argument("-j", type=int, default=1,
        help="Number of simultaneous jobs [default: %(default)s]")
    parser.add_argument("-E", action="store_true", default=False,
        help="Do not use matmodlabrc configuration file [default: False]")
    parser.add_argument("-W", choices=["std", "all", "error"], default="std",
        help="Warning level [default: %(default)s]")
    if get_f:
        parser.add_argument("source", help="Source file [default: %(default)s]")
    args = parser.parse_args(argv)

    # set runtime options
    set_runtime_opt("debug", args.dbg)
    set_runtime_opt("sqa", args.sqa)
    set_runtime_opt("nprocs", args.j)
    set_runtime_opt("verbosity", args.v)
    if args.W == "error":
        set_runtime_opt("Wall", True)
        set_runtime_opt("Werror", True)
    elif args.W == "all":
        set_runtime_opt("Wall", True)

    # directory to look for hrefs and other files
    set_runtime_opt("I", args.I)
    if args.switch:
        set_runtime_opt("switch", args.switch)
    if args.mimic:
        set_runtime_opt("mimic", args.mimic)
    if args.V:
        set_runtime_opt("viz_on_completion", True)

    if args.B and not already_wiped:
        name = args.B.strip()
        verbosity = 3 if args.v > 1 else 0
        if os.path.isfile(os.path.join(PKG_D, "{0}.so".format(name))):
            # removing is sufficient since the material class will attempt
            # to build non-existent materials
            os.remove(os.path.join(PKG_D, "{0}.so".format(name)))
        already_wiped = True

    if get_f and not os.path.isfile(args.source):
        raise FileNotFoundError(args.source)

    return args

if __name__ == "__main__":
    sys.exit(parse_sim_argv(get_f=True))
