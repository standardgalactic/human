#!/usr/bin/env bash
# =============================================================================
# Spherepop RSVP Engine  —  v2.0
# =============================================================================
#
# ARCHITECTURE
# ------------
# The world state is a *projection* derived by folding the event log through
# a pure reducer.  No field array is mutated directly; every change is first
# committed as a typed event whose payload encodes the *resolved* delta, then
# the reducer re-materialises the lattice from scratch on each render cycle.
#
# EVENT ONTOLOGY  (all stochastic outcomes resolved at generation time)
#
#   seed      | full initial field snapshot
#   pop       | x,y,kind,power,vx,vy  — cursor pop; resolved deposition follows
#   deposit   | x,y,dphi,ds           — fragment deposit on one neighbor cell
#   relax     | x,y,phi,s,vx,vy       — orb degrades to fragment
#   condense  | x,y,phi,vx,vy         — neighborhood nucleates new orb
#   diffuse   | x,y,tx,ty             — haze spreads to target cell
#   dissolve  | x,y                   — haze decays to void
#   tick      | n,delta=<k>:<f>,...   — batch event: tick n, k cell deltas
#
# RSVP FIELD CHANNELS  (per cell)
#   PHI  scalar density / presence
#   VX   x-component of directional tendency (potential gradient, not velocity)
#   VY   y-component
#   S    entropy / disorder
#   AGE  ticks since last transition
#   TAG  ontological type: void orb fragment haze wall
#
# ANISOTROPIC DEPOSITION
#   When an orb pops, fragment mass is distributed to its four cardinal
#   neighbors weighted by softmax over dot(cell_vector, direction_to_neighbor).
#   This makes deposition directionally biased by the local vector field.
#
# NEIGHBORHOOD CONDENSATION
#   A fragment may condense into an orb only when the von Neumann neighborhood
#   collectively satisfies: mean(S) <= COND_S_THRESH and sum(PHI) >= COND_PHI_MIN
#   and mean(|VX|+|VY|) >= COND_COH_THRESH (vector coherence).
#   This makes orb formation a field-scale event, not a single-cell privilege.
#
# TICK AS BATCH EVENT
#   entropy_step computes a candidate delta set against a snapshot, resolves
#   all stochasticity, then commits one 'tick' event whose payload encodes
#   every cell change.  The reducer interprets tick payloads atomically.
#
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# World geometry
# ---------------------------------------------------------------------------
W=32
H=18
SIZE=$((W * H))

# ---------------------------------------------------------------------------
# Condensation thresholds
# ---------------------------------------------------------------------------
COND_S_THRESH=3      # max mean neighborhood entropy for condensation
COND_PHI_MIN=6       # min sum of neighborhood PHI
COND_COH_THRESH=0    # min mean vector magnitude (0 = any coherence accepted)

# ---------------------------------------------------------------------------
# Global state — these are the ONLY mutable arrays; all written by reducer
# ---------------------------------------------------------------------------
declare -a CELL PHI VX VY S AGE TAG
declare -a HISTORY=()
declare -i TICK=0
declare -i CURSOR_X=$((W / 2))
declare -i CURSOR_Y=$((H / 2))
declare -i SEED=${SEED:-42}
RANDOM=$SEED

# ---------------------------------------------------------------------------
# Utility: index and bounds
# ---------------------------------------------------------------------------
idx()    { echo $(( $2 * W + $1 )); }
inside() { (( $1 >= 0 && $1 < W && $2 >= 0 && $2 < H )); }

# ---------------------------------------------------------------------------
# PRNG seeded from history length + tick + coords  (deterministic per event)
# Called once per stochastic decision; result embedded in event payload.
# ---------------------------------------------------------------------------
# _event_rand: deterministic pseudorandom value from current event context.
# Returns value in _ERAND (avoids subshell issues with set -e).
_ERAND=0
_event_rand() {
    local mix=$(( (TICK * 6271 + ${#HISTORY[@]} * 1031 + ${1:-0} * 317 + ${2:-0} * 97) % 32768 ))
    RANDOM=$(( (RANDOM ^ mix) & 32767 ))
    _ERAND=$RANDOM
}

# ---------------------------------------------------------------------------
# EVENT LOG  — append only
# ---------------------------------------------------------------------------
log_event() {
    local kind=$1; shift
    HISTORY+=("t=${TICK}|${kind}|$*")
}

# ---------------------------------------------------------------------------
# REDUCER  — pure function: given one event string, update field arrays
# ---------------------------------------------------------------------------
reduce_event() {
    local ev="$1"
    local kind payload
    kind="${ev#*|}"
    kind="${kind%%|*}"
    payload="${ev##*|}"

    case "$kind" in

    seed)
        # payload: W H then SIZE records of "i:cell:phi:vx:vy:s:age:tag"
        local -a parts
        IFS=',' read -ra parts <<< "$payload"
        local rec cell phi vx vy s age tag idx_
        for rec in "${parts[@]}"; do
            IFS=':' read -r idx_ cell phi vx vy s age tag <<< "$rec"
            CELL[$idx_]="$cell"
            PHI[$idx_]=$phi
            VX[$idx_]=$vx
            VY[$idx_]=$vy
            S[$idx_]=$s
            AGE[$idx_]=$age
            TAG[$idx_]="$tag"
        done
        ;;

    pop)
        # payload: x=N,y=N,kind=K,power=N,vx=N,vy=N
        local x y
        x=$(echo "$payload" | grep -oP 'x=\K[^,]+')
        y=$(echo "$payload" | grep -oP 'y=\K[^,]+')
        local i
        i=$(idx "$x" "$y")
        CELL[$i]='.'
        PHI[$i]=0; VX[$i]=0; VY[$i]=0; S[$i]=0; AGE[$i]=0
        TAG[$i]='void'
        ;;

    deposit)
        # payload: x=N,y=N,dphi=N,ds=N
        local x y dphi ds
        x=$(echo "$payload" | grep -oP 'x=\K[^,]+')
        y=$(echo "$payload" | grep -oP 'y=\K[^,]+')
        dphi=$(echo "$payload" | grep -oP 'dphi=\K[^,]+')
        ds=$(echo "$payload" | grep -oP 'ds=\K[^,]+')
        local i
        i=$(idx "$x" "$y")
        case "${CELL[$i]}" in
            '#') ;;  # walls absorb nothing
            '.')
                CELL[$i]='*'
                PHI[$i]=$dphi
                S[$i]=$ds
                AGE[$i]=0
                TAG[$i]='fragment'
                ;;
            '~')
                CELL[$i]='*'
                PHI[$i]=$(( PHI[$i] + dphi ))
                S[$i]=$(( S[$i] + ds ))
                TAG[$i]='fragment'
                ;;
            'o'|'*')
                PHI[$i]=$(( PHI[$i] + dphi ))
                S[$i]=$(( S[$i] + ds ))
                ;;
        esac
        ;;

    relax)
        # payload: x=N,y=N,phi=N,s=N,vx=N,vy=N
        local x y phi s vx vy
        x=$(echo "$payload" | grep -oP 'x=\K[^,]+')
        y=$(echo "$payload" | grep -oP 'y=\K[^,]+')
        phi=$(echo "$payload" | grep -oP 'phi=\K[^,]+')
        s=$(echo "$payload" | grep -oP 's=\K[^,]+')
        local i; i=$(idx "$x" "$y")
        CELL[$i]='*'; TAG[$i]='fragment'
        PHI[$i]=$phi; S[$i]=$s; AGE[$i]=0
        ;;

    condense)
        # payload: x=N,y=N,phi=N,vx=N,vy=N
        local x y phi vx vy
        x=$(echo "$payload" | grep -oP 'x=\K[^,]+')
        y=$(echo "$payload" | grep -oP 'y=\K[^,]+')
        phi=$(echo "$payload" | grep -oP 'phi=\K[^,]+')
        vx=$(echo "$payload" | grep -oP 'vx=\K[^,]+')
        vy=$(echo "$payload" | grep -oP 'vy=\K[^,]+')
        local i; i=$(idx "$x" "$y")
        CELL[$i]='o'; TAG[$i]='orb'
        PHI[$i]=$phi; VX[$i]=$vx; VY[$i]=$vy
        S[$i]=0; AGE[$i]=0
        ;;

    diffuse)
        # payload: x=N,y=N,tx=N,ty=N,s=N
        local x y tx ty s
        x=$(echo "$payload" | grep -oP 'x=\K[^,]+')
        y=$(echo "$payload" | grep -oP 'y=\K[^,]+')
        tx=$(echo "$payload" | grep -oP 'tx=\K[^,]+')
        ty=$(echo "$payload" | grep -oP 'ty=\K[^,]+')
        s=$(echo "$payload" | grep -oP 's=\K[^,]+')
        local ti; ti=$(idx "$tx" "$ty")
        if [[ "${CELL[$ti]}" == '.' ]]; then
            CELL[$ti]='~'; TAG[$ti]='haze'
            PHI[$ti]=1; S[$ti]=$s; AGE[$ti]=0
        fi
        ;;

    dissolve)
        # payload: x=N,y=N
        local x y
        x=$(echo "$payload" | grep -oP 'x=\K[^,]+')
        y=$(echo "$payload" | grep -oP 'y=\K[^,]+')
        local i; i=$(idx "$x" "$y")
        CELL[$i]='.'; TAG[$i]='void'
        PHI[$i]=0; S[$i]=0; AGE[$i]=0
        ;;

    tick)
        # payload: n=N,delta=rec1;rec2;...
        # each rec: i:cell:phi:vx:vy:s:age:tag
        local delta_str
        delta_str=$(echo "$payload" | grep -oP 'delta=\K.*')
        [[ -z "$delta_str" || "$delta_str" == "none" ]] && return
        local -a recs
        IFS=';' read -ra recs <<< "$delta_str"
        local rec idx_ cell phi vx vy s age tag
        for rec in "${recs[@]}"; do
            [[ -z "$rec" ]] && continue
            IFS=':' read -r idx_ cell phi vx vy s age tag <<< "$rec"
            CELL[$idx_]="$cell"
            PHI[$idx_]=$phi
            VX[$idx_]=$vx
            VY[$idx_]=$vy
            S[$idx_]=$s
            AGE[$idx_]=$age
            TAG[$idx_]="$tag"
        done
        ;;

    resist|miss)
        # informational only; no field change
        ;;
    esac
}

# ---------------------------------------------------------------------------
# REPLAY  — rebuild world state by folding entire history
# ---------------------------------------------------------------------------
replay_history() {
    # Reset arrays
    local i
    for (( i=0; i<SIZE; i++ )); do
        CELL[$i]='.'; PHI[$i]=0; VX[$i]=0; VY[$i]=0
        S[$i]=0; AGE[$i]=0; TAG[$i]='void'
    done
    for ev in "${HISTORY[@]}"; do
        reduce_event "$ev"
    done
}

# ---------------------------------------------------------------------------
# WORLD INITIALISATION — generates seed event with full snapshot payload
# ---------------------------------------------------------------------------
_init_arrays() {
    local i
    for (( i=0; i<SIZE; i++ )); do
        CELL[$i]='.'; PHI[$i]=0; VX[$i]=0; VY[$i]=0
        S[$i]=0; AGE[$i]=0; TAG[$i]='void'
    done
}

_apply_border() {
    local x y i
    for (( x=0; x<W; x++ )); do
        i=$(idx "$x" 0);       CELL[$i]='#'; TAG[$i]='wall'; PHI[$i]=9
        i=$(idx "$x" $((H-1))); CELL[$i]='#'; TAG[$i]='wall'; PHI[$i]=9
    done
    for (( y=0; y<H; y++ )); do
        i=$(idx 0 "$y");       CELL[$i]='#'; TAG[$i]='wall'; PHI[$i]=9
        i=$(idx $((W-1)) "$y"); CELL[$i]='#'; TAG[$i]='wall'; PHI[$i]=9
    done
}

_place_orb() {
    local x=$1 y=$2 i
    inside "$x" "$y" || return 0
    i=$(idx "$x" "$y")
    [[ "${CELL[$i]}" == '.' || "${CELL[$i]}" == '~' ]] || return 0
    CELL[$i]='o'
    PHI[$i]=$(( 2 + RANDOM % 5 ))
    VX[$i]=$(( -1 + RANDOM % 3 ))
    VY[$i]=$(( -1 + RANDOM % 3 ))
    S[$i]=$(( RANDOM % 3 ))
    AGE[$i]=0; TAG[$i]='orb'
}

_place_haze() {
    local x=$1 y=$2 i
    inside "$x" "$y" || return 0
    i=$(idx "$x" "$y")
    [[ "${CELL[$i]}" == '.' ]] || return 0
    CELL[$i]='~'; PHI[$i]=1; S[$i]=$(( 2 + RANDOM % 4 ))
    AGE[$i]=0; TAG[$i]='haze'
}

seed_world() {
    TICK=0; HISTORY=()
    RANDOM=$SEED
    _init_arrays
    _apply_border

    local n x y
    for (( n=0; n<22; n++ )); do
        x=$(( 1 + RANDOM % (W-2) ))
        y=$(( 1 + RANDOM % (H-2) ))
        _place_orb "$x" "$y"
    done
    for (( n=0; n<14; n++ )); do
        x=$(( 1 + RANDOM % (W-2) ))
        y=$(( 1 + RANDOM % (H-2) ))
        _place_haze "$x" "$y"
    done

    # Serialise full snapshot into seed event payload
    local payload="" i sep=""
    for (( i=0; i<SIZE; i++ )); do
        [[ "${CELL[$i]}" == '.' && "${TAG[$i]}" == 'void' ]] && continue
        payload+="${sep}${i}:${CELL[$i]}:${PHI[$i]}:${VX[$i]}:${VY[$i]}:${S[$i]}:${AGE[$i]}:${TAG[$i]}"
        sep=','
    done
    log_event seed "$payload"
}

# ---------------------------------------------------------------------------
# SOFTMAX DEPOSITION WEIGHTS  — anisotropic via dot(cell_vec, dir)
# Returns four weights (N E S W) as integers 0..100 summing to ~100
# ---------------------------------------------------------------------------
_softmax_weights() {
    local vx=$1 vy=$2
    # Directions: N=(0,-1) E=(1,0) S=(0,1) W=(-1,0)
    # dot products (scaled by 10 to stay integer)
    local dN=$(( 0*vx + (-1)*vy ))   # dot with north
    local dE=$(( 1*vx +   0*vy ))
    local dS=$(( 0*vx +   1*vy ))
    local dW=$((-1*vx +   0*vy ))

    # Shift all by +2 so minimum is >= 0 before softmax approximation
    dN=$(( dN + 2 )); dE=$(( dE + 2 ))
    dS=$(( dS + 2 )); dW=$(( dW + 2 ))
    (( dN < 0 )) && dN=0; (( dE < 0 )) && dE=0
    (( dS < 0 )) && dS=0; (( dW < 0 )) && dW=0

    local total=$(( dN + dE + dS + dW ))
    (( total == 0 )) && total=4 && dN=1 && dE=1 && dS=1 && dW=1

    # Return as four space-separated weights out of 100
    echo $(( dN * 100 / total )) \
         $(( dE * 100 / total )) \
         $(( dS * 100 / total )) \
         $(( dW * 100 / total ))
}

# ---------------------------------------------------------------------------
# POP  — cursor action; generates pop event + anisotropic deposit events
# ---------------------------------------------------------------------------
pop_cell() {
    local x=$1 y=$2
    inside "$x" "$y" || return 0
    local i; i=$(idx "$x" "$y")

    case "${CELL[$i]}" in
    'o')
        local power=${PHI[$i]} vx=${VX[$i]} vy=${VY[$i]}
        log_event pop "x=$x,y=$y,kind=orb,power=$power,vx=$vx,vy=$vy"
        reduce_event "${HISTORY[-1]}"

        # Compute anisotropic weights from cell's own vector
        local -a wts
        read -ra wts <<< "$(_softmax_weights "$vx" "$vy")"
        # wts: N E S W
        local -a dirs=( "0,-1" "1,0" "0,1" "-1,0" )
        local d dx dy nx ny ni dphi ds roll cumul
        for d in 0 1 2 3; do
            IFS=',' read -r dx dy <<< "${dirs[$d]}"
            nx=$(( x + dx )); ny=$(( y + dy ))
            inside "$nx" "$ny" || continue
            ni=$(idx "$nx" "$ny")
            [[ "${CELL[$ni]}" == '#' ]] && continue

            # Probabilistic deposit: roll against weight
            _event_rand "$nx" "$ny"; roll=$(( _ERAND % 100 ))
            if (( roll < wts[$d] )); then
                dphi=$(( 1 + power / 4 ))
                ds=$(( 1 + RANDOM % 2 ))
                log_event deposit "x=$nx,y=$ny,dphi=$dphi,ds=$ds"
                reduce_event "${HISTORY[-1]}"
            fi
        done
        ;;
    '*')
        log_event pop "x=$x,y=$y,kind=fragment"
        reduce_event "${HISTORY[-1]}"
        ;;
    '~')
        log_event pop "x=$x,y=$y,kind=haze"
        reduce_event "${HISTORY[-1]}"
        ;;
    '#')
        log_event resist "x=$x,y=$y,kind=wall"
        ;;
    '.')
        log_event miss "x=$x,y=$y"
        ;;
    esac
}

# ---------------------------------------------------------------------------
# NEIGHBORHOOD QUERY — von Neumann neighbors with field aggregates
# Returns: mean_s sum_phi mean_vec_mag (space separated)
# ---------------------------------------------------------------------------
_neighborhood_stats() {
    local x=$1 y=$2
    local sum_s=0 sum_phi=0 sum_vec=0 count=0
    local nx ny ni
    for pair in "0,-1" "1,0" "0,1" "-1,0"; do
        IFS=',' read -r dx dy <<< "$pair"
        nx=$(( x + dx )); ny=$(( y + dy ))
        inside "$nx" "$ny" || continue
        ni=$(idx "$nx" "$ny")
        [[ "${CELL[$ni]}" == '#' ]] && continue
        sum_s=$(( sum_s + S[$ni] ))
        sum_phi=$(( sum_phi + PHI[$ni] ))
        local mag=$(( ${VX[$ni]} * ${VX[$ni]} + ${VY[$ni]} * ${VY[$ni]} ))
        sum_vec=$(( sum_vec + mag ))
        (( count++ ))
    done
    (( count == 0 )) && { echo "99 0 0"; return; }
    echo $(( sum_s / count )) $sum_phi $(( sum_vec / count ))
}

# ---------------------------------------------------------------------------
# ENTROPY STEP  — computes full tick delta, commits single batch event
# All stochastic decisions resolved here; nothing left to chance in reducer.
# ---------------------------------------------------------------------------
entropy_step() {
    # Snapshot current state
    local -a SNAP_CELL SNAP_PHI SNAP_VX SNAP_VY SNAP_S SNAP_AGE SNAP_TAG
    local i
    for (( i=0; i<SIZE; i++ )); do
        SNAP_CELL[$i]="${CELL[$i]}"
        SNAP_PHI[$i]=${PHI[$i]}
        SNAP_VX[$i]=${VX[$i]}
        SNAP_VY[$i]=${VY[$i]}
        SNAP_S[$i]=${S[$i]}
        SNAP_AGE[$i]=${AGE[$i]}
        SNAP_TAG[$i]="${TAG[$i]}"
    done

    # Accumulate delta: only changed cells
    local delta_str=""
    local sep=""

    # Helper: queue a delta record
    _delta() {
        local idx_=$1 cell=$2 phi=$3 vx=$4 vy=$5 s=$6 age=$7 tag=$8
        # Only record if different from snapshot
        if [[ "${SNAP_CELL[$idx_]}" != "$cell" ||
              "${SNAP_PHI[$idx_]}"  != "$phi"  ||
              "${SNAP_VX[$idx_]}"   != "$vx"   ||
              "${SNAP_VY[$idx_]}"   != "$vy"   ||
              "${SNAP_S[$idx_]}"    != "$s"     ||
              "${SNAP_TAG[$idx_]}"  != "$tag"   ]]; then
            delta_str+="${sep}${idx_}:${cell}:${phi}:${vx}:${vy}:${s}:${age}:${tag}"
            sep=";"
        fi
    }

    local x y
    for (( y=1; y<H-1; y++ )); do
        for (( x=1; x<W-1; x++ )); do
            i=$(idx "$x" "$y")

            case "${SNAP_CELL[$i]}" in

            'o')
                local new_s=$(( SNAP_S[$i] ))
                local new_vx=${SNAP_VX[$i]} new_vy=${SNAP_VY[$i]}
                local new_phi=${SNAP_PHI[$i]}

                # Entropy drift
                _event_rand "$x" "$y"
                if (( _ERAND % 7 == 0 )); then
                    new_s=$(( new_s + 1 ))
                fi

                # Local entropy smoothing from neighborhood
                local mean_s _ns_phi _ns_vm
                read -r mean_s _ns_phi _ns_vm <<< "$(_neighborhood_stats "$x" "$y")"
                if (( new_s > mean_s + 2 )); then
                    new_s=$(( new_s - 1 ))
                elif (( new_s + 2 < mean_s )); then
                    new_s=$(( new_s + 1 ))
                fi

                # Vector re-seed when stagnant
                local flow=$(( SNAP_VX[$i]**2 + SNAP_VY[$i]**2 ))
                _event_rand "$x" "$y"
                if (( flow == 0 && _ERAND % 5 == 0 )); then
                    _event_rand "$x" "$y"; new_vx=$(( -1 + _ERAND % 3 ))
                    _event_rand "$x" "$y"; new_vy=$(( -1 + _ERAND % 3 ))
                fi

                # High-entropy relaxation → fragment (resolved here)
                if (( new_s >= 6 )); then
                    new_phi=$(( SNAP_PHI[$i] > 1 ? SNAP_PHI[$i] - 1 : 1 ))
                    _delta "$i" '*' "$new_phi" 0 0 "$(( new_s - 2 ))" 0 'fragment'
                else
                    _delta "$i" 'o' "$new_phi" "$new_vx" "$new_vy" "$new_s" \
                           "$(( SNAP_AGE[$i] + 1 ))" 'orb'
                fi
                ;;

            '*')
                local ns=0 nphi=0 nvm=0
                read -r ns nphi nvm <<< "$(_neighborhood_stats "$x" "$y")"

                # Neighborhood condensation — field-scale gate
                if (( SNAP_PHI[$i] >= 2 && ns <= COND_S_THRESH &&
                      nphi >= COND_PHI_MIN )); then
                    # Resolve new orb vector from neighborhood average
                    local avg_vx=0 avg_vy=0 cnt=0
                    local cnx cny cni_
                    for cpair in "0,-1" "1,0" "0,1" "-1,0"; do
                        IFS=',' read -r cdx cdy <<< "$cpair"
                        cnx=$(( x + cdx )); cny=$(( y + cdy ))
                        inside "$cnx" "$cny" || continue
                        cni_=$(idx "$cnx" "$cny")
                        avg_vx=$(( avg_vx + SNAP_VX[$cni_] ))
                        avg_vy=$(( avg_vy + SNAP_VY[$cni_] ))
                        (( cnt++ ))
                    done
                    (( cnt > 0 )) && avg_vx=$(( avg_vx / cnt )) && avg_vy=$(( avg_vy / cnt ))
                    _delta "$i" 'o' "$(( SNAP_PHI[$i] + 1 ))" \
                           "$avg_vx" "$avg_vy" 0 0 'orb'

                else
                    # Fragment → haze (age decay, resolved probabilistically here)
                    _event_rand "$x" "$y"; local _r1=$_ERAND
                    _event_rand "$x" "$y"; local _r2=$_ERAND
                    if (( SNAP_AGE[$i] > 7 && _r1 % 3 == 0 )); then
                        _delta "$i" '~' 1 0 0 "$(( 2 + _r2 % 3 ))" 0 'haze'
                    else
                        local new_sf=$(( SNAP_S[$i] ))
                        local mean_sf=0 _p2=0 _v2=0
                        read -r mean_sf _p2 _v2 <<< "$(_neighborhood_stats "$x" "$y")"
                        if (( new_sf > mean_sf + 2 )); then new_sf=$(( new_sf - 1 ))
                        elif (( new_sf + 2 < mean_sf )); then new_sf=$(( new_sf + 1 ))
                        fi
                        _delta "$i" '*' "${SNAP_PHI[$i]}" 0 0 "$new_sf" \
                               "$(( SNAP_AGE[$i] + 1 ))" 'fragment'
                    fi
                fi
                ;;

            '~')
                # Diffuse to random empty neighbor (resolved here)
                _event_rand "$x" "$y"; local _rd=$_ERAND
                if (( _rd % 5 == 0 )); then
                    _event_rand "$x" "$y"; local dir=$(( _ERAND % 4 ))
                    local -a _dxs=(-1 1 0 0) _dys=(0 0 -1 1)
                    local htx=$(( x + _dxs[$dir] )) hty=$(( y + _dys[$dir] ))
                    if inside "$htx" "$hty"; then
                        local hti; hti=$(idx "$htx" "$hty")
                        if [[ "${SNAP_CELL[$hti]}" == '.' ]]; then
                            _delta "$hti" '~' 1 0 0 "${SNAP_S[$i]}" 0 'haze'
                        fi
                    fi
                fi
                # Dissolution or age
                _event_rand "$x" "$y"; local _rdis=$_ERAND
                if (( SNAP_AGE[$i] > 9 && _rdis % 4 == 0 )); then
                    _delta "$i" '.' 0 0 0 0 0 'void'
                else
                    _delta "$i" '~' 1 0 0 "${SNAP_S[$i]}" \
                           "$(( SNAP_AGE[$i] + 1 ))" 'haze'
                fi
                ;;

            esac
        done
    done

    # Commit single tick event with full resolved delta
    (( TICK++ ))
    local tick_payload="n=${TICK},delta=${delta_str:-none}"
    log_event tick "$tick_payload"
    reduce_event "${HISTORY[-1]}"
}

# ---------------------------------------------------------------------------
# SCORING
# ---------------------------------------------------------------------------
score_world() {
    local orbs=0 frags=0 haze=0 entropy=0 i
    for (( i=0; i<SIZE; i++ )); do
        case "${CELL[$i]}" in
            'o') (( orbs++  )) ;;
            '*') (( frags++ )) ;;
            '~') (( haze++  )) ;;
        esac
        (( entropy += S[$i] ))
    done
    echo "orbs=$orbs frags=$frags haze=$haze entropy=$entropy"
}

# ---------------------------------------------------------------------------
# RENDER — ANSI terminal
# ---------------------------------------------------------------------------

# Color codes
_C_RESET='\033[0m'
_C_WALL='\033[90m'       # dark grey
_C_ORB='\033[1;33m'      # bold yellow
_C_FRAG='\033[36m'       # cyan
_C_HAZE='\033[35m'       # magenta
_C_CURSOR='\033[1;32m'   # bold green
_C_VOID='\033[90m'       # dark grey
_C_HEAD='\033[1;37m'     # bold white
_C_DIM='\033[2;37m'      # dim white
_C_INFO='\033[1;34m'     # bold blue
_C_EVENT='\033[2;36m'    # dim cyan

render() {
    printf '\033[H\033[2J'

    # Header
    printf "${_C_HEAD}  SPHEREPOP RSVP ENGINE  v2.0${_C_RESET}"
    printf "  ${_C_DIM}tick=%-4d  seed=%-6d  cursor=(%d,%d)${_C_RESET}\n" \
           "$TICK" "$SEED" "$CURSOR_X" "$CURSOR_Y"
    printf "${_C_DIM}  event-sourced · anisotropic deposition · neighborhood condensation${_C_RESET}\n"
    printf "${_C_DIM}  %-56s${_C_RESET}\n\n" "$(score_world)"

    # Field — with colored glyphs
    local x y i ch
    for (( y=0; y<H; y++ )); do
        printf '  '
        for (( x=0; x<W; x++ )); do
            i=$(idx "$x" "$y")
            ch="${CELL[$i]}"
            if (( x == CURSOR_X && y == CURSOR_Y )); then
                printf "${_C_CURSOR}@${_C_RESET}"
            else
                case "$ch" in
                    '#') printf "${_C_WALL}#${_C_RESET}" ;;
                    'o') printf "${_C_ORB}o${_C_RESET}"  ;;
                    '*') printf "${_C_FRAG}*${_C_RESET}" ;;
                    '~') printf "${_C_HAZE}~${_C_RESET}" ;;
                    '.')
                        # Show faint entropy heatmap on void cells
                        local sv=${S[$i]}
                        if (( sv > 0 )); then
                            printf "${_C_DIM}.${_C_RESET}"
                        else
                            printf ' '
                        fi
                        ;;
                esac
            fi
        done
        printf '\n'
    done

    # Vector field overlay line (cursor cell)
    local ci; ci=$(idx "$CURSOR_X" "$CURSOR_Y")
    printf "\n${_C_DIM}  cursor cell:  tag=%-8s  phi=%-3d  s=%-3d  vx=%-2d  vy=%-2d  age=%-3d${_C_RESET}\n" \
           "${TAG[$ci]}" "${PHI[$ci]}" "${S[$ci]}" \
           "${VX[$ci]}" "${VY[$ci]}" "${AGE[$ci]}"

    # History tail
    printf "\n${_C_INFO}  Recent events:${_C_RESET}\n"
    local start=0 len=${#HISTORY[@]}
    (( len > 10 )) && start=$(( len - 10 ))
    local k ev_display
    for (( k=start; k<len; k++ )); do
        ev_display="${HISTORY[$k]}"
        # Truncate long tick payloads for display
        if [[ "$ev_display" == *"|tick|"* ]]; then
            ev_display="${ev_display%%,delta=*},delta=[${#HISTORY[$k]} chars]"
        fi
        printf "${_C_EVENT}  %s${_C_RESET}\n" "$ev_display"
    done

    printf "\n${_C_DIM}  history depth: %d events   world cells: %d${_C_RESET}\n" \
           "${#HISTORY[@]}" "$SIZE"

    # Controls
    printf "\n${_C_HEAD}  Controls:${_C_RESET}"
    printf "${_C_DIM}  wasd move  |  p pop  |  g tick  |  i inspect  |  r reseed  |  q quit${_C_RESET}\n"
}

# ---------------------------------------------------------------------------
# INSPECT  — show full causal ancestry display for cursor cell
# ---------------------------------------------------------------------------
inspect_cell() {
    local x=$CURSOR_X y=$CURSOR_Y
    local ci; ci=$(idx "$x" "$y")

    printf '\033[H\033[2J'
    printf "${_C_HEAD}  CELL INSPECTOR  (%d,%d)${_C_RESET}\n\n" "$x" "$y"
    printf "  tag=%-10s  phi=%-3d  s=%-3d  vx=%-3d  vy=%-3d  age=%-3d\n\n" \
           "${TAG[$ci]}" "${PHI[$ci]}" "${S[$ci]}" \
           "${VX[$ci]}" "${VY[$ci]}" "${AGE[$ci]}"

    printf "${_C_INFO}  Events touching cell ($x,$y):${_C_RESET}\n"
    local k ev shown=0
    for (( k=0; k<${#HISTORY[@]}; k++ )); do
        ev="${HISTORY[$k]}"
        # Match events that reference this cell's coordinates
        if [[ "$ev" == *"x=${x},y=${y}"* ]] || \
           [[ "$ev" == *"x=$x,y=$y"* ]] || \
           [[ "$ev" == *"tx=${x},ty=${y}"* ]]; then
            printf "${_C_EVENT}  [%4d]  %s${_C_RESET}\n" "$k" "$ev"
            (( shown++ ))
        fi
    done
    (( shown == 0 )) && printf "  ${_C_DIM}(no direct events recorded for this cell)${_C_RESET}\n"

    printf "\n${_C_DIM}  Neighborhood:${_C_RESET}\n"
    local nx ny ni
    for pair in "0,-1" "1,0" "0,1" "-1,0"; do
        IFS=',' read -r dx dy <<< "$pair"
        nx=$(( x + dx )); ny=$(( y + dy ))
        inside "$nx" "$ny" || continue
        ni=$(idx "$nx" "$ny")
        printf "  (%2d,%2d) tag=%-8s  phi=%-3d  s=%-3d  vx=%-2d  vy=%-2d\n" \
               "$nx" "$ny" "${TAG[$ni]}" "${PHI[$ni]}" "${S[$ni]}" \
               "${VX[$ni]}" "${VY[$ni]}"
    done

    local ns nphi nvm
    read -r ns nphi nvm <<< "$(_neighborhood_stats "$x" "$y")"
    printf "\n  ${_C_DIM}neighborhood: mean_s=%-3d  sum_phi=%-3d  mean_vec_mag=%-3d${_C_RESET}\n" \
           "$ns" "$nphi" "$nvm"

    printf "\n  ${_C_DIM}condensation gate: s_ok=%s  phi_ok=%s${_C_RESET}\n" \
           "$(( ns <= COND_S_THRESH ? 1 : 0 ))" \
           "$(( nphi >= COND_PHI_MIN ? 1 : 0 ))"

    printf "\n${_C_DIM}  Press any key to return...${_C_RESET}\n"
    IFS= read -rsn1
}

# ---------------------------------------------------------------------------
# CURSOR
# ---------------------------------------------------------------------------
move_cursor() {
    local nx=$(( CURSOR_X + $1 )) ny=$(( CURSOR_Y + $2 ))
    inside "$nx" "$ny" && CURSOR_X=$nx && CURSOR_Y=$ny
}

# ---------------------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------------------
main_loop() {
    seed_world
    # Materialise world from seed event
    replay_history

    while true; do
        render
        IFS= read -rsn1 key
        case "$key" in
            w) move_cursor  0 -1 ;;
            a) move_cursor -1  0 ;;
            s) move_cursor  0  1 ;;
            d) move_cursor  1  0 ;;
            p) pop_cell "$CURSOR_X" "$CURSOR_Y" ;;
            g) entropy_step ;;
            i) inspect_cell ;;
            r)
                TICK=0; HISTORY=(); RANDOM=$SEED
                seed_world
                replay_history
                ;;
            q)
                printf '\033[H\033[2J'
                printf "${_C_HEAD}  Final world state:${_C_RESET}  $(score_world)\n\n"
                printf "${_C_INFO}  Event history  (%d entries):${_C_RESET}\n" "${#HISTORY[@]}"
                local k ev
                for (( k=0; k<${#HISTORY[@]}; k++ )); do
                    ev="${HISTORY[$k]}"
                    if [[ "$ev" == *"|tick|"* ]]; then
                        ev="${ev%%,delta=*},delta=[...]"
                    fi
                    printf "  [%4d]  %s\n" "$k" "$ev"
                done
                printf "\n${_C_DIM}  History is the ground.${_C_RESET}\n\n"
                exit 0
                ;;
        esac
    done
}

main_loop
