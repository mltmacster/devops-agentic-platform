#!/bin/bash
# =============================================================================
# DAP COMPUTE AUTOMATION — Compute Management & System Optimization
# =============================================================================
# 
# This script provides three core automation capabilities:
#   1. Kill all headless instances after test runs  
#   2. Clear caches (pytest, Python, package managers)
#   3. Audit the computer for further optimization opportunities
#
# Usage:
#   ./run_computing.sh cleanup          # Kill headless instances & clear cache
#   ./run_computing.sh audit           # Audit only (no cleanup)
#   ./run_computing.sh full            # Full cycle: audit → cleanup → report
# =============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT_DIR="$PROJECT_ROOT/.vault/scripts"

# Colors for output (Windows-compatible)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

is_windows() {
    [ -n "$MSYSTEM" ] || command -v taskkill >/dev/null 2>&1
}

# Resolve a working Python interpreter (Windows Store stubs can block `python3`)
PY_CMD="$(command -v python3 >/dev/null 2>&1 && python3 -c 'import sys' >/dev/null 2>&1 && echo python3 || echo python)"
python3() { "$PY_CMD" "$@"; }
pip3() { "$PY_CMD" -m pip "$@"; }

list_dap_pids() {
    if is_windows; then
        powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.Name -like 'python*' -and \$_.CommandLine -match 'uvicorn|dap_dashboard|start_dap|pytest' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r' || true
    else
        ps aux | grep -E "uvicorn|dap_dashboard|start_dap|pytest" | grep -v grep | awk '{print $2}' 2>/dev/null || true
    fi
}

# ============================================================
# SECTION 1: Kill Headless Instances After Test Runs
# ============================================================

kill_headless_instances() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  🧹 KILLING HEADLESS AGENT INSTANCES${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    local killed_count=0

    local pids
    pids=$(list_dap_pids)

    for pid in $pids; do
        [ -z "$pid" ] && continue
        echo -e "  ${YELLOW}Killing PID $pid (DAP headless instance)${NC}"
        if is_windows; then
            taskkill //PID "$pid" //T //F > /dev/null 2>&1 || true
        else
            kill -TERM "$pid" 2>/dev/null || true
            sleep 1
            kill -KILL "$pid" 2>/dev/null || true
        fi
        killed_count=$((killed_count + 1))
    done

    echo -e "${GREEN}✅ Killed $killed_count headless instances${NC}"

    # Verify all are gone
    local remaining
    remaining=$(list_dap_pids | wc -l 2>/dev/null || echo "0")
    if [ "$remaining" -gt 0 ]; then
        echo -e "${YELLOW}⚠ $remaining processes still running${NC}"
    fi
}

# ============================================================
# SECTION 2: Clear Cache (pytest, Python, package managers)
# ============================================================

clear_caches() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  🧹 CLEARING CACHE DIRECTORIES${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    local cleared=0
    
    # 1. pytest cache & pytest_cache directory  
    if [ -d "$PROJECT_ROOT/.pytest_cache" ]; then
        echo -e "  ${YELLOW}Removing .pytest_cache/...${NC}"
        rm -rf "$PROJECT_ROOT/.pytest_cache"
        cleared=$((cleared + 1))
    fi
    
    # 2. Python bytecode (__pycache__)
    if find "$PROJECT_ROOT" -type d -name "__pycache__" 2>/dev/null | head -1 | grep -q .; then
        echo -e "  ${YELLOW}Removing __pycache__/... directories${NC}"
        find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        cleared=$((cleared + 1))
    fi
    
    # 3. Python compile cache (.pyc files)  
    if find "$PROJECT_ROOT" -name "*.pyc" 2>/dev/null | head -1 | grep -q .; then
        echo -e "  ${YELLOW}Removing .pyc files${NC}"
        find "$PROJECT_ROOT" -name "*.pyc" -delete 2>/dev/null || true
        cleared=$((cleared + 1))
    fi
    
    # 4. pip cache  
    local pip_cache_dirs="$HOME/.cache/pip"
    if [ -n "$LOCALAPPDATA" ]; then
        pip_cache_dirs="$pip_cache_dirs $LOCALAPPDATA/pip/cache"
    fi
    for cache_dir in $pip_cache_dirs; do
        if [ -d "$cache_dir" ]; then
            echo -e "  ${YELLOW}Removing pip cache ($cache_dir)${NC}"
            rm -rf "$cache_dir"
            cleared=$((cleared + 1))
        fi
    done
    
    # 5. pipenv cache (if applicable)  
    if [ -d "$HOME/.local/share/pipenv" ]; then
        echo -e "  ${YELLOW}Removing pipenv cache${NC}"
        rm -rf "$HOME/.local/share/pipenv"
        cleared=$((cleared + 1))
    fi
    
    # 6. Poetry cache (if applicable)  
    if [ -d "$HOME/.cache/poetry" ]; then
        echo -e "  ${YELLOW}Removing poetry cache${NC}"
        rm -rf "$HOME/.cache/poetry"
        cleared=$((cleared + 1))
    fi
    
    # 7. mypy cache (if present)  
    if [ -d "$PROJECT_ROOT/.mypy_cache" ]; then
        echo -e "  ${YELLOW}Removing .mypy_cache/...${NC}"
        rm -rf "$PROJECT_ROOT/.mypy_cache"
        cleared=$((cleared + 1))
    fi
    
    # 8. IPython cache (if present)  
    if [ -d "$PROJECT_ROOT/.ipython_cache" ]; then
        echo -e "  ${YELLOW}Removing .ipython_cache/...${NC}"
        rm -rf "$PROJECT_ROOT/.ipython_cache" 2>/dev/null || true
    fi
    
    # 9. IPython profiles cache (if present)  
    if [ -d "$PROJECT_ROOT/.ipython_profile" ]; then
        echo -e "  ${YELLOW}Removing .ipython_profile/...${NC}"
        rm -rf "$PROJECT_ROOT/.ipython_profile" 2>/dev/null || true
    fi
    
    # 10. IDE caches (VS Code, PyCharm) - user-controlled  
    echo ""
    echo -e "${YELLOW}IDE caches (manual cleanup recommended):${NC}"
    echo "  • VS Code: .vscode/workspace.json workspace cache"
    echo "  • PyCharm: ~/.cache/pycharm/<version>/index/ directory"
    echo ""
    
    echo -e "${GREEN}✅ Cleared $cleared cache directories${NC}"
}

# ============================================================
# SECTION 3: System Audit (Optimization Opportunities)
# ============================================================

audit_computer() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  🔍 COMPUTE AUDIT — OPTIMIZATION OPPORTUNITIES${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    local audit_score=0
    local total_checks=0
    
    # ── Check 1: Disk Space ────────────────────────────────
    total_checks=$((total_checks + 1))
    echo -e "\n${YELLOW}📊 Disk Space Usage${NC}"
    
    # Cross-platform disk usage detection
    local disk_info=""
    if command -v df &> /dev/null; then
        # Find the Use% field from the right (filesystem labels can contain spaces)
        disk_info=$(df -h / 2>/dev/null | awk 'NR==2 {for (i = NF; i > 0; i--) if ($i ~ /%$/) {print $i; exit}}' || echo "unknown")
    else
        # Windows: get C: drive free space
        disk_info=$(wmic logicaldisk where "deviceid='C:'" get freespace,caption 2>/dev/null || echo "unknown")
    fi
    
    local disk_pct=""
    
    if [ "$disk_info" != "unknown" ]; then
        # Extract percentage and numeric value  
        if echo "$disk_info" | grep -q "%"; then
            disk_pct=$(echo "$disk_info" | tr -d '%')
        else
            # Try to parse numeric value (e.g., "13649800 KB")
            disk_pct=$(echo "$disk_info" | tr -dc '0-9' | head -c 5)
        fi
        
        # Handle Windows disk usage (>80% threshold)  
        if [ -n "$disk_pct" ] && [[ "$disk_pct" =~ ^[0-9]+$ ]]; then
            if [ "$disk_pct" -gt 80 ]; then
                echo -e "  ${RED}⚠ WARNING: Disk usage at ~${disk_pct}%${NC}"
                echo -e "    → Consider cleaning /tmp, /var/cache, or old packages"
                echo -e "    → Command: find /tmp -type f -atime +30 -delete"
                audit_score=$((audit_score - 10))
            elif [ "$disk_pct" -gt 60 ]; then
                echo -e "  ${YELLOW}⚠ WARNING: Disk usage at ~${disk_pct}%${NC}"
                echo -e "    → Consider cleaning /tmp, /var/cache, or old packages"
                echo -e "    → Command: find /tmp -type f -atime +30 -delete"
                audit_score=$((audit_score - 5))
            else
                echo -e "  ${GREEN}✓ Disk usage at ~${disk_pct}% — healthy${NC}"
                audit_score=$((audit_score + 10))
            fi
        else
            echo -e "  ${YELLOW}⚠ Could not parse disk usage: $disk_info${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠ Could not determine disk usage${NC}"
    fi
    
    # ── Check 2: Python Environment Health ───────────────────
    total_checks=$((total_checks + 1))
    echo -e "\n${YELLOW}🐍 Python Environment Health${NC}"
    
    # Check for multiple Python versions causing confusion  
    if is_windows; then
        local python_versions=$(where python 2>/dev/null | grep -v WindowsApps | sort -u)
    else
        local python_versions=$(which -a python3 2>/dev/null | xargs awk '{print $NF}' | LC_ALL=C sort -u)
    fi
    local version_count=$(echo "$python_versions" | grep -c . 2>/dev/null || echo "1")
    
    if [ "$version_count" -gt 1 ]; then
        echo -e "  ${RED}⚠ WARNING: Multiple Python versions detected${NC}"
        echo -e "    → This may cause import conflicts"
        echo -e "    → Consider using a virtualenv or conda environment"
        audit_score=$((audit_score - 10))
    else
        echo -e "  ${GREEN}✓ Single Python version: $(python3 --version 2>&1)${NC}"
        audit_score=$((audit_score + 10))
    fi
    
    # Check for stale pip packages (not in requirements)  
    local venv_dir="$PROJECT_ROOT/.venv"
    if [ -d "$venv_dir" ]; then
        local installed=$(python3 -m pip list 2>/dev/null | grep -E "(numpy|pandas|requests|fastapi|uvicorn|httpx|pytest)" || echo "")
        
        local unused=$(comm -23 <(echo "$installed" | sort) <(cat "$PROJECT_ROOT/requirements.txt" 2>/dev/null | grep -v '^#' | grep -v '^$' | tr '[:space:]' '\n') 2>/dev/null || echo "none")
        
        if [ -n "$unused" ]; then
            local unused_count=$(echo "$unused" | wc -l)
            echo -e "  ${YELLOW}⚠ $unused_count unused packages found${NC}"
            echo -e "    → Command: python3 -m pip freeze --requirements=requirements.txt | grep -v '\[installed\|extra\]' | xargs pip uninstall"
            audit_score=$((audit_score - 5))
        else
            echo -e "  ${GREEN}✓ No unused packages detected${NC}"
            audit_score=$((audit_score + 10))
        fi
    else
        echo -e "  ${GREEN}✓ No virtual environment found (using system Python)${NC}"
        audit_score=$((audit_score + 5))
    fi
    
    # ── Check 3: Memory Usage ───────────────────────────────
    total_checks=$((total_checks + 1))
    echo -e "\n${YELLOW}💾 Memory Usage${NC}"
    
    local mem_info=""
    if command -v free &> /dev/null; then
        mem_info=$(free -h 2>/dev/null || free -m | head -1)
    elif is_windows; then
        # Windows: "0 <totalMB> <usedMB>" (wmic is deprecated on modern Windows)
        mem_info=$(powershell.exe -NoProfile -Command "\$o=Get-CimInstance Win32_OperatingSystem; \$t=[int](\$o.TotalVisibleMemorySize/1024); \$u=[int]((\$o.TotalVisibleMemorySize-\$o.FreePhysicalMemory)/1024); Write-Output ('0 {0}MB {1}MB' -f \$t,\$u)" 2>/dev/null || echo "unknown")
    else
        mem_info="unknown"
    fi
    
    if [ "$mem_info" != "unknown" ]; then
        local mem_total=$(echo "$mem_info" | awk '{print $2}' 2>/dev/null || echo "unknown")
        local mem_used=$(echo "$mem_info" | awk '{print $3}' 2>/dev/null || echo "unknown")
        
        if [ "$mem_used" != "unknown" ]; then
            local mem_pct=0
            
            if command -v python3 &> /dev/null; then
                # Parse memory values (handle "16G" format)
                mem_pct=$(python3 -c "
import re, math
total_str = '$mem_total'
used_str = '$mem_used'

def parse_mem(s):
    s = s.strip()
    m = re.match(r'(\d+\.?\d*)\s*([KMGT]B)?', s)
    if not m: return 0
    val = float(m.group(1))
    unit = m.group(2) or 'B'
    multipliers = {'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
    return val * multipliers.get(unit, 1)

total_bytes = parse_mem(total_str)
used_bytes = parse_mem(used_str)
print(int(used_bytes * 100 / total_bytes) if total_bytes > 0 else 0)" 2>/dev/null || echo "unknown")
            fi
            
            if [ "$mem_pct" != "unknown" ]; then
                if [ "$mem_pct" -gt 80 ]; then
                    echo -e "  ${RED}⚠ WARNING: Memory usage at ~${mem_pct}%${NC}"
                    echo -e "    → Consider running: free -m && rm /tmp/*"
                    audit_score=$((audit_score - 10))
                elif [ "$mem_pct" -gt 60 ]; then
                    echo -e "  ${YELLOW}⚠ WARNING: Memory usage at ~${mem_pct}%${NC}"
                    echo -e "    → Consider running: free -m"
                    audit_score=$((audit_score - 5))
                else
                    echo -e "  ${GREEN}✓ Memory usage at ~${mem_pct}% — healthy${NC}"
                    audit_score=$((audit_score + 10))
                fi
            else
                echo -e "  ${YELLOW}⚠ Could not determine memory usage${NC}"
            fi
        else
            echo -e "  ${YELLOW}⚠ Could not determine memory usage${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠ Could not determine memory usage${NC}"
    fi
    
    # ── Check 4: Open Network Connections ───────────────────
    total_checks=$((total_checks + 1))
    echo -e "\n${YELLOW}🌐 Network Connections${NC}"
    
    local listening_ports=""
    if is_windows; then
        listening_ports=$(netstat -ano 2>/dev/null | grep LISTENING || true)
    elif command -v ss &> /dev/null; then
        listening_ports=$(ss -tlnp 2>/dev/null | grep LISTEN || true)
    elif command -v netstat &> /dev/null; then
        listening_ports=$(netstat -tlnp 2>/dev/null | grep LISTEN || true)
    fi
    
    local port_count=0
    if [ -n "$listening_ports" ]; then
        port_count=$(echo "$listening_ports" | wc -l 2>/dev/null || echo "0")
    fi
    
    if [ "$port_count" -gt 10 ]; then
        echo -e "  ${YELLOW}⚠ $port_count listening ports detected${NC}"
        echo -e "    → Consider what's truly needed"
        audit_score=$((audit_score - 5))
    else
        echo -e "  ${GREEN}✓ $port_count listening ports — healthy${NC}"
        audit_score=$((audit_score + 10))
    fi
    
    # ── Check 5: Process Count ───────────────────────────────
    total_checks=$((total_checks + 1))
    echo -e "\n⚙️ Process Count"
    
    local process_count=$(ps aux | wc -l 2>/dev/null || echo "0")
    if is_windows; then
        local python_count=$(powershell.exe -NoProfile -Command "(Get-Process python* -ErrorAction SilentlyContinue | Measure-Object).Count" 2>/dev/null || echo "0")
    else
        local python_count=$(ps aux | grep -c "python" 2>/dev/null || echo "0")
    fi
    
    echo -e "  Total processes: $process_count"
    echo -e "  Python processes: $python_count"
    
    if [ "$process_count" -gt 200 ]; then
        echo -e "  ${RED}⚠ WARNING: High process count (${process_count})${NC}"
        audit_score=$((audit_score - 10))
    elif [ "$process_count" -gt 100 ]; then
        echo -e "  ${YELLOW}⚠ WARNING: Elevated process count (${process_count})${NC}"
        echo -e "    → Consider what's running in the background"
        audit_score=$((audit_score - 5))
    else
        echo -e "  ${GREEN}✓ Process count at $process_count — healthy${NC}"
        audit_score=$((audit_score + 10))
    fi
    
    # ── Check 6: CPU Usage ───────────────────────────────────
    total_checks=$((total_checks + 1))
    echo -e "\n🔥 CPU Usage"
    
    # Get current CPU load average (1-min)  
    local cpu_load=""
    if [ -f /proc/loadavg ] && ! is_windows; then
        cpu_load=$(cat /proc/loadavg 2>/dev/null | awk '{print $1}' || echo "unknown")
    else
        cpu_load="unknown"
    fi
    
    if [ "$cpu_load" != "unknown" ]; then
        echo -e "  1-min load average: $cpu_load"
        
        # Get CPU cores count  
        local cpu_cores=""
        if command -v nproc &> /dev/null; then
            cpu_cores=$(nproc 2>/dev/null || echo "unknown")
        elif [ -f /proc/cpuinfo ]; then
            cpu_cores=$(grep -c "processor" /proc/cpuinfo 2>/dev/null || echo "unknown")
        fi
        
        if [ "$cpu_cores" != "unknown" ]; then
            local load_per_core=""
            
            if command -v python3 &> /dev/null; then
                load_per_core=$(python3 -c "print(round($cpu_load / $cpu_cores, 2))" 2>/dev/null || echo "unknown")
            else
                load_per_core=$(echo "$cpu_load / $cpu_cores" | awk '{printf "%.2f", $1/$2}' 2>/dev/null || echo "unknown")
            fi
            
            if [ "$load_per_core" != "unknown" ]; then
                # Check if load is high (more than 80% of cores utilized)  
                local threshold=""
                if command -v python3 &> /dev/null; then
                    threshold=$(python3 -c "print($cpu_cores * 0.8)" 2>/dev/null || echo "${cpu_cores}")
                fi
                
                if command -v python3 &> /dev/null; then
                    local is_high=$(python3 -c "print('yes' if $cpu_load > ($threshold) else 'no')" 2>/dev/null || echo "no")
                else
                    is_high="no"
                fi
                
                if [ "$is_high" == "yes" ]; then
                    echo -e "  ${RED}⚠ WARNING: High CPU utilization (${load_per_core}/core)${NC}"
                    echo -e "    → Consider reducing concurrent agent instances"
                    audit_score=$((audit_score - 10))
                elif command -v python3 &> /dev/null; then
                    local is_medium=$(python3 -c "print('yes' if $cpu_load > ($threshold / 2) else 'no')" 2>/dev/null || echo "no")
                    if [ "$is_medium" == "yes" ]; then
                        echo -e "  ${YELLOW}⚠ WARNING: Elevated CPU utilization (${load_per_core}/core)${NC}"
                        echo -e "    → Consider monitoring for background processes"
                        audit_score=$((audit_score - 5))
                    fi
                else
                    echo -e "  ${GREEN}✓ CPU utilization at ${load_per_core}/core — healthy${NC}"
                    audit_score=$((audit_score + 10))
                fi
            fi
        else
            echo -e "  ${YELLOW}⚠ Could not determine CPU core count${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠ Could not determine CPU load${NC}"
    fi
    
    # ── Check 7: Python Package Health ──────────────────────
    total_checks=$((total_checks + 1))
    echo -e "\n📦 Python Package Health"
    
    # Check for known problematic packages  
    local pip_list=""
    if command -v python3 &> /dev/null; then
        pip_list=$(python3 -m pip list 2>/dev/null | grep -E "(numpy|pandas|requests|fastapi|uvicorn|httpx|pytest)" || echo "")
    fi
    
    if [ -n "$pip_list" ]; then
        # Check for security vulnerabilities (simple check)  
        local vuln_count=0
        if command -v python3 &> /dev/null; then
            vuln_count=$(pip3 list --format=json 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
vulns = [p for p in data if any(k in (p.get('name','').lower(), p.get('original_name','').lower()) 
             for k in ['requests', 'urllib3', 'cryptography'])]
print(len(vulns))" 2>/dev/null || echo "0")
        fi
        
        if [ "$vuln_count" != "0" ]; then
            echo -e "  ${YELLOW}⚠ $vuln_count packages may need security updates${NC}"
            echo -e "    → Command: pip3 install --upgrade requests urllib3 cryptography"
            audit_score=$((audit_score - 5))
        else
            echo -e "  ${GREEN}✓ No known vulnerable packages in key dependencies${NC}"
            audit_score=$((audit_score + 10))
        fi
    else
        echo -e "  ${YELLOW}⚠ No key packages found or pip not available${NC}"
    fi
    
    # ── Check 8: Log File Size ───────────────────────────────
    total_checks=$((total_checks + 1))
    echo -e "\n📝 Log File Check"
    
    local log_files=""
    if [ -d "$PROJECT_ROOT" ]; then
        log_files=$(find "$PROJECT_ROOT" -name "*.log" -type f 2>/dev/null | head -10 || true)
    fi
    
    if [ -n "$log_files" ]; then
        echo -e "  Found log files:"
        for log in $log_files; do
            local size=$(du -h "$log" 2>/dev/null | cut -f1 || echo "unknown")
            echo -e "    $size $log"
        done
        
        # Check for oversized logs (>10MB)  
        local big_logs=""
        if [ -d "$PROJECT_ROOT" ]; then
            big_logs=$(find "$PROJECT_ROOT" -name "*.log" -type f -size +10M 2>/dev/null | head -5 || true)
        fi
        if [ -n "$big_logs" ]; then
            echo -e "  ${RED}⚠ Large log files detected — consider rotation${NC}"
            audit_score=$((audit_score - 5))
        fi
    else
        echo -e "  ${GREEN}✓ No log files found${NC}"
        audit_score=$((audit_score + 10))
    fi
    
    # ── Check 9: Network Port Conflicts ─────────────────────
    total_checks=$((total_checks + 1))
    echo -e "\n🔌 Port Availability Check"
    
    local common_ports="80 443 8000 8001 8080 9000 3000 5432 6379"
    
    for port in $common_ports; do
        local in_use=0
        if is_windows; then
            netstat -ano 2>/dev/null | grep -i LISTENING | grep -Eq "[:.]$port[[:space:]]" && in_use=1
        elif ss -tlnp 2>/dev/null | grep -q ":$port:" || netstat -tlnp 2>/dev/null | grep -q ":$port"; then
            in_use=1
        fi
        if [ "$in_use" -eq 1 ]; then
            echo -e "  ${YELLOW}Port $port is in use${NC}"
        else
            echo -e "  ${GREEN}Port $port is available${NC}"
        fi
    done
    
    # ── Final Score & Summary ───────────────────────────────
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  📊 AUDIT SUMMARY${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    local max_score=$((total_checks * 10))
    local score_pct=0
    
    if [ $max_score -gt 0 ]; then
        score_pct=$((audit_score * 100 / max_score))
    fi
    
    echo ""
    
    if [ "$score_pct" -ge 80 ]; then
        echo -e "  ${GREEN}🎉 Score: $score_pct/${max_score} — System is healthy!${NC}"
    elif [ "$score_pct" -ge 50 ]; then
        echo -e "  ${YELLOW}⚠ Score: $score_pct/${max_score} — Some improvements needed${NC}"
    else
        echo -e "  ${RED}❌ Score: $score_pct/${max_score} — Significant issues found${NC}"
    fi
    
    echo ""
    echo -e "${YELLOW}💡 Quick Actions:${NC}"
    echo "  - Run './run_computing.sh cleanup' to kill headless instances & clear cache"
    echo "  - Run './run_computing.sh full' for audit + cleanup + report"
    echo "  - Clean up /tmp: find /tmp -type f -atime +30 -delete"
    echo "  - Clean up old logs: find $PROJECT_ROOT -name '*.log' -mtime +30 -delete"
    echo "  - Clean Python cache: find $PROJECT_ROOT -type d -name '__pycache__' -exec rm -rf {} +"
    
    echo ""
}

# ============================================================
# MAIN: Parse Arguments & Execute
# ============================================================

main() {
    local action="${1:-full}"
    
    case "$action" in
        cleanup|clean)
            echo -e "${BLUE}Running CLEANUP mode${NC}"
            kill_headless_instances
            clear_caches
            ;;
        audit|scan)
            echo -e "${BLUE}Running AUDIT mode${NC}"
            audit_computer
            ;;
        full|all)
            echo -e "${BLUE}Running FULL cycle: Audit → Cleanup${NC}"
            audit_computer
            echo ""
            kill_headless_instances
            clear_caches
            ;;
        *)
            echo -e "${RED}Usage: $0 {full|cleanup|audit}${NC}"
            echo ""
            echo -e "  ${YELLOW}full${NC}    — Run audit, then kill instances & clear cache"
            echo -e "  ${YELLOW}cleanup${NC} — Kill headless instances & clear cache only"
            echo -e "  ${YELLOW}audit${NC}   — Run system audit only (no cleanup)"
            echo ""
            exit 1
            ;;
    esac
}

main "$@"
