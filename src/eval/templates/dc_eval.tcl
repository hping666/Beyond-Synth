# Beyond-Synth DC evaluation template: one script for every DC rung and hidden configuration
# (docs/spec/01-eval-service.md §2). Driven by environment variables set by src/eval/dc.py; the compile
# command itself comes from config/experiments.yaml (configs.<name>.compile).
#
#   EVAL_VERILOG      RTL files (space separated)         EVAL_TOP          top module
#   EVAL_FORMAT       verilog | sverilog                  EVAL_INCDIRS      `include search dirs
#   EVAL_LIB_DB       .db files (space separated)         EVAL_LIB_NAME     library name
#   EVAL_DONT_USE     lib cells to exclude (optional)
#   EVAL_SDC          Synopsys-ready SDC (already unit scaled; from src/eval/sdc.py)
#   EVAL_CLK_NAME     clock name in the SDC              EVAL_CLK_PERIOD   expected period in library units
#   EVAL_OUT          report directory                    EVAL_COMPILE      e.g. "compile_ultra -retime -gate_clock"
#   EVAL_MAX_CORES    set_host_options -max_cores         EVAL_MAX_FANOUT   set_max_fanout value
#   EVAL_MODE         wireload | topo (topo = dc_shell -topographical_mode; required for -spg)
#   EVAL_MW_REF / EVAL_MW_TF   Milkyway reference library / technology file (topo only)
#   EVAL_CG_STYLE     extra set_clock_gating_style arguments (optional)
#   EVAL_SAIF / EVAL_SAIF_INSTANCE   switching activity for report_power (optional)
#   EVAL_FLOW_DIR     directory holding sdc_compat.tcl (the read-only flow/ scripts)
#
# DC returns 0 on failure instead of raising (eda-knowledge/05-traps.md #1): every command runs through `step`,
# which checks both the Tcl exception and the return value. The SDC section is bracketed by markers built from
# a variable so that the Python side can find errors DC only printed (#2, #3). Nothing here is design specific.

proc envq {name def} {
    if {[info exists ::env($name)] && $::env($name) ne ""} { return $::env($name) }
    return $def
}

set SYN        [envq SYNOPSYS ""]
set VFILES     [envq EVAL_VERILOG ""]
set TOP        [envq EVAL_TOP ""]
set VFMT       [envq EVAL_FORMAT verilog]
set INCDIRS    [envq EVAL_INCDIRS ""]
set LIB_DB     [envq EVAL_LIB_DB ""]
set LIB_NAME   [envq EVAL_LIB_NAME ""]
set DONT_USE   [envq EVAL_DONT_USE ""]
set SDC        [envq EVAL_SDC ""]
set CLK_NAME   [envq EVAL_CLK_NAME clk]
set CLK_PERIOD [envq EVAL_CLK_PERIOD ""]
set OUT        [envq EVAL_OUT "."]
set COMPILE    [envq EVAL_COMPILE "compile_ultra"]
set MAX_CORES  [envq EVAL_MAX_CORES 4]
set MAX_FANOUT [envq EVAL_MAX_FANOUT 20]
set MODE       [envq EVAL_MODE wireload]
set MW_REF     [envq EVAL_MW_REF ""]
set MW_TF      [envq EVAL_MW_TF ""]
set CG_STYLE   [envq EVAL_CG_STYLE ""]
set SAIF       [envq EVAL_SAIF ""]
set SAIF_INST  [envq EVAL_SAIF_INSTANCE ""]
set FLOWDIR    [envq EVAL_FLOW_DIR /hdd1/hping/eda/flow]

file mkdir $OUT
set STATUS  ok
set FAILMSG ""
set SAIF_STATUS "none"
set CHECK_ERRORS -1

# run one DC command: a Tcl exception is a failure, and so is a return value of 0
proc step {label script} {
    global STATUS FAILMSG
    if {$STATUS ne "ok"} { return 0 }
    if {[catch {uplevel 1 $script} r]} {
        set STATUS $label
        set FAILMSG $r
        return 0
    }
    if {[string is integer -strict $r] && $r == 0} {
        set STATUS $label
        set FAILMSG "command returned 0 (DC reported an error; see the log)"
        return 0
    }
    return 1
}

# ---------------- reproducibility and reporting settings ----------------
if {[catch {set_host_options -max_cores $MAX_CORES} e]} {
    set STATUS setup_failed
    set FAILMSG "set_host_options: $e"
}
catch { set_app_var report_default_significant_digits 6 }
set_app_var sh_new_variable_message false
suppress_message {VER-130 VER-936 UID-401 OPT-1206 LINT-52}

# ---------------- libraries ----------------
set LIB_DIRS {}
foreach db $LIB_DB { lappend LIB_DIRS [file dirname $db] }
set search_path [concat $search_path [lsort -unique $LIB_DIRS]]
if {$INCDIRS ne ""} { set search_path [concat $search_path $INCDIRS] }
set target_library    $LIB_DB
set synthetic_library [list $SYN/libraries/syn/dw_foundation.sldb]
set link_library      [concat * $target_library $synthetic_library]
set symbol_library    {}

# ---------------- topographical mode (needed by -spg) ----------------
if {$STATUS eq "ok" && $MODE eq "topo"} {
    if {$MW_REF eq "" || $MW_TF eq ""} {
        set STATUS constraint_failed
        set FAILMSG "topo mode needs EVAL_MW_REF and EVAL_MW_TF (only nangate45 has a Milkyway library)"
    } else {
        set_app_var mw_reference_library $MW_REF
        set mwdes $OUT/../mw_design
        # a stale design library makes create_mw_lib return 0 silently and compile fail later (traps #8)
        if {[file exists $mwdes]} { file delete -force $mwdes }
        set _mwok 0
        if {[catch {set _mwok [create_mw_lib -technology $MW_TF -mw_reference_library $MW_REF -open $mwdes]} e]} {
            set STATUS constraint_failed
            set FAILMSG "create_mw_lib failed: $e"
        } elseif {[string is integer -strict $_mwok] && $_mwok == 0} {
            set STATUS constraint_failed
            set FAILMSG "create_mw_lib returned 0 (see the log)"
        }
    }
}
if {$STATUS eq "ok" && $MODE ne "topo" && [string match "*-spg*" $COMPILE]} {
    set STATUS constraint_failed
    set FAILMSG "-spg needs topographical mode"
}

# ---------------- read the design ----------------
foreach f $VFILES {
    step analyze_failed { analyze -format $VFMT $f }
}
step elaborate_failed { elaborate $TOP }
if {$STATUS eq "ok" && [sizeof_collection [get_designs -quiet $TOP]] == 0} {
    set STATUS elaborate_failed
    set FAILMSG "no design '$TOP' after elaborate (top name mismatch?)"
}
step link_failed { current_design $TOP ; link }
step link_failed { uniquify }
if {$STATUS eq "ok"} {
    redirect $OUT/check_design.rpt { catch { check_design -nosplit } }
    set CHECK_ERRORS 0
    if {![catch {set fh [open $OUT/check_design.rpt r]}]} {
        foreach line [split [read $fh] "\n"] {
            if {[string match "Error*" [string trim $line]]} { incr CHECK_ERRORS }
        }
        close $fh
    }
}
if {$STATUS eq "ok"} {
    foreach c $DONT_USE { catch { set_dont_use [get_lib_cells -quiet "*/$c"] } }
}

# ---------------- constraints ----------------
if {$STATUS eq "ok" && $SDC eq ""} {
    set STATUS constraint_failed
    set FAILMSG "no SDC given (EVAL_SDC)"
}
if {$STATUS eq "ok" && ![file exists $SDC]} {
    set STATUS constraint_failed
    set FAILMSG "SDC file not found: $SDC"
}
if {$STATUS eq "ok" && [catch {source $FLOWDIR/sdc_compat.tcl} e]} {
    set STATUS constraint_failed
    set FAILMSG "loading sdc_compat.tcl failed: $e"
}
set _MK "###SDC"
if {$STATUS eq "ok"} {
    echo "${_MK}_BEGIN###"
    if {[catch {source $SDC} err]} {
        set STATUS constraint_failed
        set FAILMSG "SDC failed: $err"
    }
    echo "${_MK}_END###"
}
if {$STATUS eq "ok" && [sizeof_collection [all_clocks]] == 0} {
    set STATUS constraint_failed
    set FAILMSG "no clock after the SDC"
}
if {$STATUS eq "ok" && $CLK_PERIOD ne ""} {
    if {[catch {set _p [get_attribute [get_clocks $CLK_NAME] period]} e]} {
        set STATUS constraint_failed
        set FAILMSG "clock '$CLK_NAME' missing: $e"
    } elseif {abs($_p - $CLK_PERIOD) > 1e-6 * (1.0 + abs($CLK_PERIOD))} {
        set STATUS constraint_failed
        set FAILMSG "clock period $_p differs from the expected $CLK_PERIOD"
    }
}
if {$STATUS eq "ok"} {
    catch { set_max_fanout $MAX_FANOUT [current_design] }
    if {[catch {write_sdc $OUT/applied_constraints.sdc}]} {
        set STATUS constraint_failed
        set FAILMSG "write_sdc failed"
    } else {
        set fh [open $OUT/applied_constraints.sdc r]
        set dump [read $fh]
        close $fh
        set n_in 0
        if {[catch {set n_in [sizeof_collection [snps_all_inputs_no_clocks]]}]} {
            catch { set n_in [sizeof_collection [all_inputs]] }
        }
        if {$n_in > 0 && ![string match "*set_input_delay*" $dump]} {
            set STATUS constraint_failed
            set FAILMSG "applied constraints contain no set_input_delay: the SDC did not execute completely"
        }
    }
}

# ---------------- compile ----------------
if {$STATUS eq "ok" && [string match "*-gate_clock*" $COMPILE] && $CG_STYLE ne ""} {
    if {[catch {eval set_clock_gating_style $CG_STYLE} e]} {
        set STATUS constraint_failed
        set FAILMSG "set_clock_gating_style: $e"
    }
}
set ELAPSED 0
if {$STATUS eq "ok"} {
    set t0 [clock seconds]
    step compile_failed { eval $COMPILE }
    set ELAPSED [expr {[clock seconds] - $t0}]
}
if {$STATUS eq "ok"} {
    set ncells [sizeof_collection [get_cells -quiet -hier -filter "is_hierarchical == false"]]
    if {$ncells == 0} {
        set STATUS empty_netlist
        set FAILMSG "no leaf cells after compile"
    }
}

# ---------------- reports ----------------
if {$STATUS eq "ok"} {
    redirect $OUT/qor.rpt        { report_qor -nosplit }
    redirect $OUT/area.rpt       { report_area -nosplit }
    redirect $OUT/area_hier.rpt  { report_area -hierarchy -nosplit }
    redirect $OUT/timing.rpt     { report_timing -max_paths 10 -nworst 1 -input_pins -transition_time -capacitance -nosplit }
    redirect $OUT/refs.rpt       { report_reference -hierarchy -nosplit }
    redirect $OUT/resources.rpt  { report_resources -hierarchy -nosplit }
    redirect $OUT/hierarchy.rpt  { report_hierarchy -nosplit }
    if {[string match "*-gate_clock*" $COMPILE]} {
        redirect $OUT/clock_gating.rpt { catch { report_clock_gating -nosplit } }
    }
    redirect $OUT/power_default.rpt { report_power -nosplit }
    if {$SAIF ne ""} {
        set inst $SAIF_INST
        if {$inst eq ""} { set inst $TOP }
        if {[catch {read_saif -input $SAIF -instance $inst -auto_map_names} e]} {
            set SAIF_STATUS "read_failed: [string map [list \n { }] $e]"
        } else {
            set SAIF_STATUS ok
            redirect $OUT/saif.rpt       { catch { report_saif -nosplit } }
            redirect $OUT/power_saif.rpt { report_power -nosplit }
        }
    }
    catch { write -format verilog -hierarchy -output $OUT/netlist.v }
    catch { write -format ddc -hierarchy -output $OUT/design.ddc }
    catch { write_sdc $OUT/design.sdc }
    set fh [open $OUT/metrics.txt w]
    catch { puts $fh "wns=[get_attribute [get_timing_paths -delay_type max] slack]" }
    catch { puts $fh "leaf_cells=[sizeof_collection [get_cells -quiet -hier -filter {is_hierarchical == false}]]" }
    catch { puts $fh "registers=[sizeof_collection [all_registers]]" }
    catch { puts $fh "hier_cells=[sizeof_collection [get_cells -quiet -hier -filter {is_hierarchical == true}]]" }
    close $fh
}

set fh [open $OUT/status.txt w]
puts $fh "status=$STATUS"
puts $fh "mode=$MODE"
puts $fh "compile=$COMPILE"
puts $fh "elapsed=$ELAPSED"
puts $fh "check_errors=$CHECK_ERRORS"
puts $fh "saif=$SAIF_STATUS"
puts $fh "error=[string map [list \n { } \r { }] $FAILMSG]"
close $fh
exit
