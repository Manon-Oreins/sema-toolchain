import argparse
import sys


class ArgumentParserSCDG:
    # TODO customize for other tools
    def __init__(self, tcw):
        self.tcw = tcw

    def parse_arguments(self, allow_unk = False):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--method",
            help="Method used for the analysis among (DFS,BFS,CBFS) (default : DFS)",
        )
        parser.add_argument(
            "--n_args",
            help="Number of symbolic arguments given to the binary (default : 0)",
            type=int,
        )
        parser.add_argument(
            "--timeout",
            help="Timeout in seconds before ending extraction (default : 600)",
            type=int,
        )
        parser.add_argument(
            "--symb_loop",
            help="Number of iteration allowed for a symbolic loop (default : 3) ",
            type=int,
        )
        parser.add_argument(
            "--conc_loop",
            help="Number of symbolic arguments given to the binary (default : 1024)",
            type=int,
        )
        parser.add_argument(
            "--simul_state",
            help="Number of simultaneous states we explore with simulation manager (default : 5)",
            default=5,
            type=int,
        )
        parser.add_argument(
            "--limit_pause",
            help="Number of states allowed in pause stash (default : 200)",
            type=int,
        )
        parser.add_argument(
            "--max_step",
            help="Maximum number of steps allowed for a state (default : 50 000)",
            type=int,
        )
        parser.add_argument(
            "--max_deadend",
            help="Number of deadended state required to stop (default : 600)",
            type=int,
        )
        parser.add_argument(
            "--min_size",
            help="Minimum size required for a trace to be used in SCDG (default : 3)",
            default=3,
            type=int,
        )
        parser.add_argument(
            "--not_resolv_string",
            help="Do we try to resolv references of string (default : False)",
            action="store_true",
        )
        parser.add_argument(
            "--disjoint_union",
            help="Do we merge traces or use disjoint union ? (default : merge)",
            action="store_true",
        )
        parser.add_argument(
            "--not_comp_args",
            help="Do we compare arguments to add new nodes when building graph ? (default : comparison enabled)",
            action="store_true",
        )
        parser.add_argument(
            "--not_ignore_zero",
            help="Do we ignore zero when building graph ? (default : Discard zero)",
            action="store_true",
        )
        parser.add_argument(
            "--dir",
            help=" Directory to save outputs graph for gspan  (default : output/)",
        )
        parser.add_argument(
            "--exp_dir",
            help=" Directory to save SCDG extracted (default : output/save-SCDG/)",
            default="output/save-SCDG/",
        )
        parser.add_argument(
            "--discard_SCDG",
            help="Do not keep intermediate SCDG in file  (default : False)",
            action="store_false",
        )
        parser.add_argument(
            "--eval_time",
            help="Keep intermediate SCDG in file  (default : False)",
            action="store_true",
        )
        parser.add_argument(
            "--verbose",
            help="Verbose output during calls extraction  (default : False)",
            action="store_true",
        )
        parser.add_argument(
            "--debug_error",
            help="Debug error states (default : False)",
            action="store_true",
        )
        parser.add_argument(
            "--format_out",
            help="Format to save graph output : gs or json (Default: gs)",
            default="gs",
        )
        parser.add_argument(
            "--packed",
            help="Is the binary packed ? (default : False)",
            action="store_true",
        )
        parser.add_argument(
            "--unpack_method",
            help="unpack with Symbion (linux only | todo) or with unipacker (windows only) [symbion|unipacker]\nTrue if --packed is set with symbion as default",
        )
        parser.add_argument(
            "--concrete_target_is_local",
            action="store_true",
            help="Use a local GDB server instead of using cuckoo (default : False)",
        )
        parser.add_argument(
            "--familly",
            help="Use a local GDB server instead of using cuckoo (default : False)",
        )
        parser.add_argument("binary", help="Name of the binary to analyze")
        
        args = None
        if not allow_unk:
            args = parser.parse_args()
        else:
            args, unknown = parser.parse_known_args()

        nameFile = args.binary
        if not self.tcw.print_on:
            self.tcw.print_on = args.verbose
        self.tcw.debug_error = args.debug_error
        sys.setrecursionlimit(2000)
        if args.method:
            expl_method = args.method.upper()
            if expl_method not in ["BFS", "DFS", "CDFS", "CBFS"]:
                self.tcw.log.info("Method of exploration not recognized")
                self.tcw.log.info("Changed to default DFS")
                expl_method = "DFS"
        else:
            expl_method = "DFS"

        familly = "unknown"
        if args.familly:
            familly = args.familly
        args.exp_dir = args.exp_dir + familly + "/"

        if args.timeout:
            self.tcw.timeout = args.timeout
        if args.symb_loop:
            self.tcw.jump_it = args.symb_loop
        if args.conc_loop:
            self.tcw.loop_counter_concrete = args.conc_loop
        if args.eval_time:
            self.tcw.eval_time = True

        self.tcw.max_simul_state = args.simul_state

        self.tcw.string_resolv = not args.not_resolv_string
        if args.limit_pause:
            self.tcw.max_in_pause_stach = args.limit_pause
        if args.max_step:
            self.tcw.max_step = args.max_step
        if args.max_deadend:
            self.tcw.max_end_state = args.max_deadend
        
        self.tcw.is_packed = args.packed
        if self.tcw.is_packed:
            self.tcw.unpack_mode = "symbion"

        if args.concrete_target_is_local:
            self.tcw.concrete_target_is_local = True
        if args.unpack_method:
            mode = args.unpack_method
            if mode in ["unipacker", "symbion"]:
                self.tcw.log.info("Unpack with %s",mode)
                self.tcw.unpack_mode = mode
                self.tcw.is_packed = True
            else:
                #TODO
                pass

        return args, nameFile, expl_method, familly