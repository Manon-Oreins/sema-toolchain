#!/usr/bin/env python3
import os
import sys

# for pypy3
# sys.path.insert(0, '/usr/local/lib')
# sys.path.insert(0, os.path.expanduser('~/lib'))
# sys.path.insert(0, os.path.expanduser('/home/crochetch/Documents/toolchain_malware_analysis/penv/lib'))

import json as json_dumper
from builtins import open as open_file
import threading
import time
#from tkinter import E

# from submodules.claripy import claripy
import claripy
import monkeyhex  # this will format numerical results in hexadecimal
import logging
from capstone import *

# Syscall table stuff
import angr

# Personnal stuf
try:
    from .helper.GraphBuilder import *
    from .procedures.CustomSimProcedure import *
    from .plugin.PluginEnvVar import *
    from .explorer.ToolChainExplorerDFS import ToolChainExplorerDFS
    from .explorer.ToolChainExplorerCDFS import ToolChainExplorerCDFS
    from .explorer.ToolChainExplorerBFS import ToolChainExplorerBFS
    from .explorer.ToolChainExplorerCBFS import ToolChainExplorerCBFS
    from .clogging.CustomFormatter import CustomFormatter
    from .helper.ArgumentParserSCDG import ArgumentParserSCDG
except:
    from helper.GraphBuilder import *
    from procedures.CustomSimProcedure import *
    from plugin.PluginEnvVar import *
    from explorer.ToolChainExplorerDFS import ToolChainExplorerDFS
    from explorer.ToolChainExplorerCDFS import ToolChainExplorerCDFS
    from explorer.ToolChainExplorerBFS import ToolChainExplorerBFS
    from explorer.ToolChainExplorerCBFS import ToolChainExplorerCBFS
    from clogging.CustomFormatter import CustomFormatter
    from helper.ArgumentParserSCDG import ArgumentParserSCDG

import subprocess
import nose
import avatar2 as avatar2

import angr
import claripy


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class ToolChainSCDG:
    """
    TODO
    """

    def __init__(
        self,
        timeout=600,
        max_end_state=600,
        max_step=50000,
        timeout_tab=[1200, 2400, 3600],
        jump_it=1,
        loop_counter_concrete=102400,
        jump_dict={},
        jump_concrete_dict={},
        max_simul_state=5,
        max_in_pause_stach=500,
        fast_main=False,
        force_symbolique_return=False,
        string_resolv=True,
        print_on=False,
        print_sm_step=False,
        print_syscall=False,
        debug_error=False,
        debug_string=False,
        is_from_tc = False
    ):
        self.start_time = time.time()
        self.timeout = timeout  # In seconds
        self.max_end_state = max_end_state
        self.max_step = max_step
        self.timeout_tab = timeout_tab

        # Option relative to loop
        self.jump_it = jump_it
        self.loop_counter_concrete = loop_counter_concrete
        self.jump_dict = jump_dict
        self.jump_concrete_dict = jump_concrete_dict

        # Options relative to stash management
        self.max_simul_state = max_simul_state
        self.max_in_pause_stach = max_in_pause_stach

        self.fast_main = fast_main
        self.force_symbolique_return = force_symbolique_return

        self.print_on = print_on
        self.print_sm_step = print_sm_step
        self.print_syscall = print_syscall
        self.debug_error = debug_error
        self.debug_string = debug_string

        self.scdg = []
        self.scdg_fin = []

        logging.getLogger("angr").setLevel("WARNING")
        # logging.getLogger('angr').setLevel('INFO')

        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(CustomFormatter())
        self.log = logging.getLogger("ToolChainSCDG")
        self.log.setLevel(logging.INFO)
        self.log.addHandler(ch)
        self.log.propagate = False

        self.call_sim = CustomSimProcedure(
            self.scdg, self.scdg_fin, 
            string_resolv=string_resolv, print_on=print_on, 
            print_syscall=print_syscall, is_from_tc=is_from_tc
        )
        self.eval_time = False

    def build_scdg(self, args, nameFile, expl_method, family):
        # Create directory to store SCDG if it doesn't exist
        self.scdg.clear()
        self.scdg_fin.clear()
        self.call_sim.syscall_found.clear()
        self.call_sim.system_call_table.clear()
        try:
            os.stat(args.exp_dir)
        except:
            os.makedirs(args.exp_dir)

        if args.exp_dir != "output/save-SCDG/"+family+"/":
            setup = open_file(args.exp_dir + "setup.txt", "w")
            setup.write(str(self.jump_it) + "\n")
            setup.write(str(self.loop_counter_concrete) + "\n")
            setup.write(str(self.max_simul_state) + "\n")
            setup.write(str(self.max_in_pause_stach) + "\n")
            setup.write(str(self.max_step) + "\n")
            setup.write(str(self.max_end_state))
            setup.close()

        # Take name of the sample without full path
        if "/" in nameFile:
            nameFileShort = nameFile.split("/")[-1]
        else:
            nameFileShort = nameFile

        title = "--- Building SCDG of " + nameFileShort + " ---"
        self.log.info("\n" + "-" * len(title) + "\n" + title + "\n" + "-" * len(title))

        #####################################################
        ##########      Project creation         ############
        #####################################################
        """
        TODO : Note for further works : support_selfmodifying_code should be investigated
        """

        # Load a binary into a project = control base
        proj = angr.Project(
            nameFile,
            use_sim_procedures=True,
            load_options={
                "auto_load_libs": True
            },  # ,load_options={"auto_load_libs":False}
            support_selfmodifying_code=True,
            # arch="",
        )

        # Getting from a binary file to its representation in a virtual address space
        main_obj = proj.loader.main_object
        os_obj = main_obj.os

        # Informations about program
        if self.print_on:
            self.log.info("Libraries used are :\n" + str(proj.loader.requested_names))
            self.log.info("OS recognized as : " + str(os_obj))
            self.log.info("CPU architecture recognized as : " + str(proj.arch))
            self.log.info(
                "Entry point of the binary recognized as : " + str(proj.entry)
            )
            self.log.info(
                "Min/Max addresses of the binary recognized as : " + str(proj.loader)
            )
            self.log.info(
                "Stack executable ?  " + str(main_obj.execstack)
            )  # TODO could be use for heuristic ?
            self.log.info("Binary position-independent ?  " + str(main_obj.pic))
            self.log.info("Exploration method:  " + str(expl_method))

        # Defining arguments given to the program (minimum is filename)
        args_binary = [nameFileShort]
        if args.n_args:
            for i in range(args.n_args):
                args_binary.append(claripy.BVS("arg" + str(i), 8 * 16))

        # Load pre-defined syscall table
        if os_obj == "windows":
            self.call_sim.system_call_table = self.call_sim.ddl_loader.load(proj)
        else:
            self.call_sim.system_call_table = self.call_sim.linux_loader.load_table(
                proj
            )

        # TODO : Maybe useless : Try to directly go into main (optimize some binary in windows)
        addr_main = proj.loader.find_symbol("main")
        if addr_main and self.fast_main:
            addr = addr_main.rebased_addr
        else:
            addr = None

        # Create initial state of the binary
        # options = {angr.options.USE_SYSTEM_TIMES}
        options = {angr.options.SIMPLIFY_MEMORY_READS}
        options.add(angr.options.ZERO_FILL_UNCONSTRAINED_REGISTERS)
        options.add(angr.options.USE_SYSTEM_TIMES)
        options.add(angr.options.ZERO_FILL_UNCONSTRAINED_MEMORY)
        options.add(angr.options.SIMPLIFY_MEMORY_READS)
        options.add(angr.options.SIMPLIFY_MEMORY_WRITES)
        options.add(angr.options.SIMPLIFY_CONSTRAINTS)
        # options.add(angr.options.SYMBOLIC_WRITE_ADDRESSES)
        options.add(angr.options.SYMBOLIC_INITIAL_VALUES)
        if self.debug_error:
            pass
            # options.add(angr.options.TRACK_JMP_ACTIONS)
            # options.add(angr.options.TRACK_CONSTRAINT_ACTIONS)
            # options.add(angr.options.TRACK_JMP_ACTIONS)

        # Contains a program's memory, registers, filesystem data... any "live data" that can be changed by execution has a home in the state
        self.log.info("Entry_state address = " + str(addr))

        state = proj.factory.entry_state(
            addr=addr, args=args_binary, add_options=options
        )

        state.options.discard("LAZY_SOLVES")
        state.register_plugin(
            "heap", angr.state_plugins.heap.heap_ptmalloc.SimHeapPTMalloc()
        )
        # For environment variable mainly
        state.register_plugin( 
            "plugin_env_var", PluginEnvVar()
        )  

        # Memory block to store environment variable
        state.plugin_env_var.env_block = state.heap.malloc(32767)
        for i in range(32767):
            c = state.solver.BVS("c_env_block{}".format(i), 8)
            state.memory.store(state.plugin_env_var.env_block + i, c)
        if os_obj == "windows" :
            ComSpec = "ComSpec=C:\Windows\system32\cmd.exe\0".encode("utf-8")
            ComSpec_bv = state.solver.BVV(ComSpec)
            state.memory.store(state.plugin_env_var.env_block, ComSpec_bv)
            state.plugin_env_var.env_var["COMSPEC"] = "C:\Windows\system32\cmd.exe\0"
        state.plugin_env_var.expl_method = expl_method

        # Constraint arguments to ASCII
        for i in range(1, len(args_binary)):
            for byte in args_binary[i].chop(8):
                # state.add_constraints(byte != '\x00') # null
                state.add_constraints(byte >= " ")  # '\x20'
                state.add_constraints(byte <= "~")  # '\x7e'

        # Creation of file with concrete content for cleanware
        # TODO WORK in Progress, need to think about automation of the process (like an argument with file name to create)
        if False:
            clean_files = ["share/file/magic.mgc"]
            for n in clean_files:
                f = open_file("malware-inputs/clean/" + n, "rb")
                cont = f.read()
                simfile = angr.SimFile(n, content=cont)
                f.close()
                simfile.set_state(state)

        #### Custom Hooking ####
        # Mechanism by which angr replaces library code with a python summary
        # When performing simulation, at every step angr checks if the current
        # address has been hooked, and if so, runs the hook instead of the binary
        # code at that address.

        if os_obj == "windows":
            self.call_sim.loadlibs(proj)
        
        self.call_sim.custom_hook_static(proj)

        if os_obj != "windows":
            self.call_sim.custom_hook_no_symbols(proj)
        else:
            # pass
            self.call_sim.custom_hook_windows_symbols(proj)

        # Creation of simulation manager, primary interface in angr for performing execution
        simgr = proj.factory.simulation_manager(state)

        #####################################################
        ##########         Exploration           ############
        #####################################################

        # Improved "Break point"
        state.inspect.b("simprocedure", when=angr.BP_AFTER, action=self.call_sim.add_call)
        state.inspect.b("simprocedure", when=angr.BP_BEFORE, action=self.call_sim.add_call_debug)
        state.inspect.b("call", when=angr.BP_BEFORE, action=self.call_sim.add_addr_call)
        state.inspect.b("call", when=angr.BP_AFTER, action=self.call_sim.rm_addr_call)

        dump_file = {}
        self.print_memory_info(main_obj, dump_file)

        # Improved Break point for debugging purpose for specific read/write/instructions
        if self.debug_error:
            pass
            # state.inspect.b('instruction',when=angr.BP_BEFORE, action=debug_instr)
            # state.inspect.b('mem_read',when=angr.BP_BEFORE, action=debug_read)
            # state.inspect.b('mem_write',when=angr.BP_BEFORE, action=debug_write)

        # TODO : make plugins out of these globals values
        # Globals is a simple dict already managed by Angr which is deeply copied from states to states
        simgr.active[0].globals["id"] = 0
        simgr.active[0].globals["JumpExcedeed"] = False
        simgr.active[0].globals["JumpTable"] = {}
        simgr.active[0].globals["n_steps"] = 0
        simgr.active[0].globals["last_instr"] = 0
        simgr.active[0].globals["counter_instr"] = 0
        simgr.active[0].globals["loaded_libs"] = {}
        simgr.active[0].globals["addr_call"] = []

        self.scdg.append(
            [
                {
                    "name": "main",
                    "args": [str(args) for args in args_binary],
                    "addr": state.addr,
                    "ret": "symbolic",
                    "addr_func": state.addr,
                }
            ]
        )

        self.jump_dict[0] = {}
        self.jump_concrete_dict[0] = {}

        # The stash where states are moved to wait
        # until some space becomes available in Active stash.
        # The size of the space in this stash is a parameter of
        # the toolchain. If new states appear and there is no
        # space available in the Pause stash, some states are
        # dropped.
        simgr.stashes["pause"] = []

        # The stash where states leading to new
        # instruction addresses (not yet explored) of the binary
        # are kept. If CDFS or CBFS are not used, this stash
        # merges with the pause stash.
        simgr.stashes["new_addr"] = []

        # The stash where states exceeding the
        # threshold related to number of steps are moved. If
        # new states are needed and there is no state available
        # in pause stash, states in this stash are used to resume
        # exploration (their step counter are put back to zero).
        simgr.stashes["ExcessLoop"] = []

        # The stash where states which exceed the
        # threshold related to loops are moved. If new states
        # are needed and there is no state available in pause
        # or ExcessStep stash, states in this stash are used to
        # resume exploration (their loop counter are put back
        # to zero).
        simgr.stashes["ExcessStep"] = []

        simgr.stashes["temp"]

        exploration_tech = ToolChainExplorerDFS(
            simgr, 0, args.exp_dir, nameFileShort, self
        )
        if expl_method == "CDFS":
            exploration_tech = ToolChainExplorerCDFS(
                simgr, 0, args.exp_dir, nameFileShort, self
            )
        elif expl_method == "CBFS":
            exploration_tech = ToolChainExplorerCBFS(
                simgr, 0, args.exp_dir, nameFileShort, self
            )
        elif expl_method == "BFS":
            exploration_tech = ToolChainExplorerBFS(
                simgr, 0, args.exp_dir, nameFileShort, self
            )

        simgr.use_technique(exploration_tech)

        self.log.info(
            "\n------------------------------\nStart -State of simulation manager :\n "
            + str(simgr)
            + "\n------------------------------"
        )

        simgr.run()

        self.log.info(
            "\n------------------------------\nEnd - State of simulation manager :\n "
            + str(simgr)
            + "\n------------------------------"
        )

        self.log.info("Syscall Found:" + str(self.call_sim.syscall_found))

        elapsed_time = time.time() - self.start_time
        self.log.info("Total execution time to build scdg: " + str(elapsed_time))


        self.build_scdg_fin(args, nameFileShort, main_obj, state, simgr)

        g = GraphBuilder(
            name=nameFileShort,
            mapping="mapping.txt",
            merge_call=(not args.disjoint_union),
            comp_args=(not args.not_comp_args),
            min_size=args.min_size,
            ignore_zero=(not args.not_ignore_zero),
            odir=args.dir,
            verbose=args.verbose,
            familly=family
        )
        g.build_graph(self.scdg_fin, format_out=args.format_out)

    def build_scdg_fin(self, args, nameFileShort, main_obj, state, simgr):
        dump_file = {}
        dump_id = 0
        dic_hash_SCDG = {}
        # Add all traces with relevant content to graph construction
        for stateDead in simgr.deadended:
            hashVal = hash(str(self.scdg[stateDead.globals["id"]]))
            if hashVal not in dic_hash_SCDG:
                dic_hash_SCDG[hashVal] = 1
                dump_file[dump_id] = {
                    "status": "deadendend",
                    "trace": self.scdg[stateDead.globals["id"]],
                }
                dump_id = dump_id + 1
                self.scdg_fin.append(self.scdg[state.globals["id"]])

        for state in simgr.active:
            hashVal = hash(str(self.scdg[state.globals["id"]]))
            if hashVal not in dic_hash_SCDG:
                dic_hash_SCDG[hashVal] = 1
                dump_file[dump_id] = {
                    "status": "active",
                    "trace": self.scdg[state.globals["id"]],
                }
                dump_id = dump_id + 1
                self.scdg_fin.append(self.scdg[state.globals["id"]])

        for error in simgr.errored:
            hashVal = hash(str(self.scdg[state.globals["id"]]))
            if hashVal not in dic_hash_SCDG:
                dic_hash_SCDG[hashVal] = 1
                dump_file[dump_id] = {
                    "status": "errored",
                    "trace": self.scdg[error.state.globals["id"]],
                }
                dump_id = dump_id + 1
                self.scdg_fin.append(self.scdg[state.globals["id"]])

        for state in simgr.stashes["ExcessLoop"]:
            hashVal = hash(str(self.scdg[state.globals["id"]]))
            if hashVal not in dic_hash_SCDG:
                dic_hash_SCDG[hashVal] = 1
                dump_file[dump_id] = {
                    "status": "ExcessLoop",
                    "trace": self.scdg[state.globals["id"]],
                }
                dump_id = dump_id + 1
                self.scdg_fin.append(self.scdg[state.globals["id"]])

        for state in simgr.stashes["ExcessStep"]:
            hashVal = hash(str(self.scdg[state.globals["id"]]))
            if hashVal not in dic_hash_SCDG:
                dic_hash_SCDG[hashVal] = 1
                dump_file[dump_id] = {
                    "status": "ExcessStep",
                    "trace": self.scdg[state.globals["id"]],
                }
                dump_id = dump_id + 1
                self.scdg_fin.append(self.scdg[state.globals["id"]])

        for state in simgr.unconstrained:
            hashVal = hash(str(self.scdg[state.globals["id"]]))
            if hashVal not in dic_hash_SCDG:
                dic_hash_SCDG[hashVal] = 1
                dump_file[dump_id] = {
                    "status": "unconstrained",
                    "trace": self.scdg[state.globals["id"]],
                }
                dump_id = dump_id + 1
                self.scdg_fin.append(self.scdg[state.globals["id"]])

        self.print_memory_info(main_obj, dump_file)
        if args.discard_SCDG:
            # self.log.info(dump_file)
            ofilename = args.exp_dir + nameFileShort + "_SCDG.json"
            self.log.info(ofilename)
            save_SCDG = open_file(ofilename, "w")
            # self.log.info(dump_file)
            json_dumper.dump(dump_file, save_SCDG)  # ,indent=4)
            save_SCDG.close()

    def print_memory_info(self, main_obj, dump_file):
        dump_file["sections"] = {}
        for sec in main_obj.sections:
            name = sec.name.replace("\x00", "")
            info_sec = {
                "vaddr": sec.vaddr,
                "memsize": sec.memsize,
                "is_readable": sec.is_readable,
                "is_writable": sec.is_writable,
                "is_executable": sec.is_executable,
            }
            dump_file["sections"][name] = info_sec
            self.log.info(name)
            self.log.info(dump_file["sections"][name])

def main():
    toolc = ToolChainSCDG(
        print_sm_step=True,
        print_syscall=True,
        debug_error=True,
        debug_string=True,
        print_on=True,
    )
    args_parser = ArgumentParserSCDG(toolc)
    args, nameFile, expl_method, familly = args_parser.parse_arguments()

    if os.path.isfile(nameFile):
        toolc.log.info("You decide to analyse a single binary: "+ nameFile)
        toolc.build_scdg(args, nameFile, expl_method, familly)
    else:
        last_familiy = "unknown"
        if os.path.isdir(nameFile):
            subfolder = [os.path.join(nameFile, f) for f in os.listdir(nameFile) if os.path.isdir(os.path.join(nameFile, f))]
            for folder in subfolder:
                toolc.log.info("You are currently building SCDG for " + folder)
                files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
                for file  in files:
                    args.exp_dir = args.exp_dir.exp_dir.replace(last_familiy,folder.split("/")[-1])
                    toolc.build_scdg(args, file, expl_method,folder.split("/")[-1])
                toolc.families += last_familiy
                last_familiy = folder.split("/")[-1]
        else:
            toolc.log.info("Error: you should insert a folder containing malware classified in their family folders\n(Example: databases/malware-inputs/Sample_paper")
            exit(-1)

if __name__ == "__main__":
    main()