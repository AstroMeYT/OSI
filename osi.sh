#!/usr/bin/env bash

# ==============================================================================
# OSI (OriginSourceInstall) - A Source-First Package Manager for Linux
# File: osi.sh
# Description: Streamlines source-based builds using structured .instruct files.
# Syncs with JSON format managed by osi_db_manager.py
# ==============================================================================

set -e # Exit on critical unhandled errors

# Color Definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Filepaths and URLs
OSI_DIR="$HOME/.local/share/osi"
OSI_CACHE_DIR="$HOME/.cache/osi"
LOCAL_DB="$OSI_CACHE_DIR/packages.json"
INSTALLED_REGISTRY="$OSI_DIR/installed_packages.json"

# Remote DB URL pointing to GitHub repository
REMOTE_DB_URL="https://raw.githubusercontent.com/AstroMeYT/OSI/main/packages.json"

# Create necessary directories
mkdir -p "$OSI_DIR"
mkdir -p "$OSI_CACHE_DIR"

# Ensure basic tooling exists
check_prerequisites() {
    local missing_tools=()
    for tool in curl git jq; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done

    if [ ${#missing_tools[@]} -ne 0 ]; then
        echo -e "${YELLOW}Missing prerequisites: ${missing_tools[*]}.${NC}"
        echo -e "Attempting to install missing prerequisites..."
        detect_system_base
        
        case "$SYSTEM_BASE" in
            debian)
                sudo apt-get update && sudo apt-get install -y "${missing_tools[@]}"
                ;;
            redhat)
                sudo dnf install -y "${missing_tools[@]}"
                ;;
            arch)
                sudo pacman -Sy --noconfirm "${missing_tools[@]}"
                ;;
            *)
                echo -e "${RED}Error: Cannot auto-install prerequisites. Please install manually: ${missing_tools[*]}${NC}"
                exit 1
                ;;
        esac
    fi
}

# System base detection
detect_system_base() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_ID="$ID"
        OS_LIKE="$ID_LIKE"
    else
        echo -e "${RED}Error: Cannot detect system type (/etc/os-release missing).${NC}"
        exit 1
    fi

    # Classify base system
    if [[ "$OS_ID" =~ (debian|ubuntu|mint) ]] || [[ "$OS_LIKE" =~ (debian|ubuntu) ]]; then
        SYSTEM_BASE="debian"
        SYSTEM_PM="apt-get"
    elif [[ "$OS_ID" =~ (fedora|centos|rhel) ]] || [[ "$OS_LIKE" =~ (fedora|rhel) ]]; then
        SYSTEM_BASE="redhat"
        SYSTEM_PM="dnf"
    elif [[ "$OS_ID" =~ (arch|manjaro) ]] || [[ "$OS_LIKE" =~ arch ]]; then
        SYSTEM_BASE="arch"
        SYSTEM_PM="pacman"
    else
        SYSTEM_BASE="unknown"
        SYSTEM_PM="unknown"
    fi
}

# Database management (JSON formats)
sync_database() {
    echo -e "${BLUE}Syncing packages database from remote...${NC}"
    # Added -fsSL to fail on HTTP errors
    if curl -fsSL -o "$LOCAL_DB" "$REMOTE_DB_URL"; then
        echo -e "${GREEN}Database updated successfully!${NC}"
    else
        echo -e "${RED}Warning: Failed to fetch database (HTTP error or offline). Operating with cached copy if available.${NC}"
        if [ ! -f "$LOCAL_DB" ]; then
            echo -e "${YELLOW}No database cached. Initializing local workspace database...${NC}"
            echo "[]" > "$LOCAL_DB"
        fi
    fi
    
    # Initialize the installed packages tracking DB if it doesn't exist
    if [ ! -f "$INSTALLED_REGISTRY" ] || [ ! -s "$INSTALLED_REGISTRY" ]; then
        echo "[]" > "$INSTALLED_REGISTRY"
    fi

    # Ensure permissions are retained for the invoking user instead of sticking to root
    if [ -n "$SUDO_USER" ]; then
        chown -R "$SUDO_USER" "$OSI_DIR" "$OSI_CACHE_DIR" 2>/dev/null || true
    fi
}

# Help Menu Interface
show_help() {
    echo -e "${BLUE}OSI (OriginSourceInstall) - Help Menu${NC}"
    echo -e "=========================================================="
    echo -e "Usage: osi <command> [arguments]\n"
    echo -e "Commands:"
    echo -e "  ${GREEN}install <pack-name>${NC}  Installs a package from the database"
    echo -e "  ${GREEN}search <query>${NC}       Searches for packages inside the database"
    echo -e "  ${GREEN}remove <pack-name>${NC}   Removes an installed package from the system"
    echo -e "  ${GREEN}list${NC}                 Lists all packages installed via OSI"
    echo -e "  ${GREEN}help${NC}                 Opens this informative help guide"
    echo -e "=========================================================="
}

# Search functionality utilizing JQ
search_package() {
    local query="$1"
    if [ -z "$query" ]; then
        echo -e "${RED}Error: Search query cannot be empty.${NC}"
        exit 1
    fi

    echo -e "${BLUE}Searching for '${query}' in the JSON database...${NC}"
    
    local results
    # Use JQ arguments to prevent code injection, parse case-insensitive containing matches
    results=$(jq -r --arg q "$query" '.[] | select((.name | ascii_downcase | contains($q | ascii_downcase)) or (.description | ascii_downcase | contains($q | ascii_downcase)) or (.author | ascii_downcase | contains($q | ascii_downcase))) | "\(.name)|\(.author)|\(.git_url)|\(.description)"' "$LOCAL_DB" 2>/dev/null || true)

    if [ -z "$results" ]; then
        echo -e "${YELLOW}No packages matching '${query}' found.${NC}"
    else
        echo -e "\n${CYAN}Found Packages:${NC}"
        echo -e "=========================================================="
        echo "$results" | while IFS='|' read -r name author git_url desc; do
            echo -e "${GREEN}• $name${NC} (by $author)"
            if [ -n "$git_url" ] && [ "$git_url" != "None" ]; then
                echo -e "  ${PURPLE}Source: ${NC}$git_url"
            fi
            if [ -n "$desc" ] && [ "$desc" != "None" ]; then
                echo -e "  ${NC}Description: $desc"
            fi
            echo -e "----------------------------------------------------------"
        done
    fi
}

# List installed packages
list_installed() {
    if [ ! -f "$INSTALLED_REGISTRY" ]; then
        echo -e "${YELLOW}No packages installed yet.${NC}"
        return
    fi

    local installed_list
    installed_list=$(jq -r '.[] | "\(.name)|\(.author)|\(.install_date)|\(.install_path)"' "$INSTALLED_REGISTRY" 2>/dev/null || true)

    if [ -z "$installed_list" ]; then
         echo -e "${YELLOW}No packages currently installed via OSI.${NC}"
    else
        echo -e "${BLUE}Installed Packages via OSI:${NC}"
        echo -e "=========================================================="
        echo "$installed_list" | while IFS='|' read -r name author idate ipath; do
            echo -e "${GREEN}$name${NC} (by $author)"
            echo -e "  Installed on: $idate"
            echo -e "  Install path: $ipath"
            echo -e "----------------------------------------------------------"
        done
    fi
}

# Yes/No prompt wrapper
prompt_yes_no() {
    local message="$1"
    while true; do
        read -rp "$(echo -e "${YELLOW}$message [y/n]: ${NC}")" yn
        case $yn in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

# Remove/Uninstall Functionality
remove_package() {
    local pack_name="$1"
    if [ -z "$pack_name" ]; then
        echo -e "${RED}Error: Please specify a package to remove.${NC}"
        exit 1
    fi

    # Verify installation status via JQ
    local db_check
    db_check=$(jq -r --arg n "$pack_name" '.[] | select(.name == $n) | .install_path' "$INSTALLED_REGISTRY" 2>/dev/null || true)

    if [ -z "$db_check" ]; then
        echo -e "${RED}Error: Package '$pack_name' is not recorded as installed via OSI.${NC}"
        exit 1
    fi

    if prompt_yes_no "Are you sure you want to remove '$pack_name'?"; then
        echo -e "${BLUE}Removing '$pack_name'...${NC}"
        if [ -d "$db_check" ] && [[ "$db_check" == "$HOME/Applications/"* || "$db_check" == "/opt/"* || "$db_check" == "/tmp/osi-build/"* ]]; then
            echo -e "Deleting installation directory: $db_check"
            rm -rf "$db_check"
        fi

        # Remove entry from tracking database array
        jq --arg n "$pack_name" 'map(select(.name != $n))' "$INSTALLED_REGISTRY" > "${INSTALLED_REGISTRY}.tmp" && mv "${INSTALLED_REGISTRY}.tmp" "$INSTALLED_REGISTRY"

        # Ensure registry remains owned by the original user
        if [ -n "$SUDO_USER" ]; then
            chown "$SUDO_USER" "$INSTALLED_REGISTRY" 2>/dev/null || true
        fi

        echo -e "${GREEN}Package '$pack_name' has been removed successfully.${NC}"
    else
        echo -e "${YELLOW}Removal canceled.${NC}"
    fi
}

# The main Installer Process
install_package() {
    local pack_name="$1"
    if [ -z "$pack_name" ]; then
        echo -e "${RED}Error: Please specify a package to install.${NC}"
        exit 1
    fi

    # Check if already installed
    local already_installed
    already_installed=$(jq -r --arg n "$pack_name" '.[] | select(.name == $n) | .name' "$INSTALLED_REGISTRY" 2>/dev/null || true)
    
    if [ -n "$already_installed" ]; then
        if ! prompt_yes_no "Package '$pack_name' is already installed. Do you want to reinstall it?"; then
            echo -e "${YELLOW}Installation aborted.${NC}"
            exit 0
        fi
    fi

    # Fetch instructions from localized JSON database mapping
    echo -e "${BLUE}Querying package information for '$pack_name'...${NC}"
    local pkg_info
    pkg_info=$(jq -r --arg n "$pack_name" '.[] | select(.name == $n) | "\(.name)|\(.author)|\(.git_url)|\(.instruct_url)"' "$LOCAL_DB" 2>/dev/null | head -n 1)

    if [ -z "$pkg_info" ]; then
        echo -e "${RED}Error: Package '$pack_name' not found in database.${NC}"
        exit 1
    fi

    IFS='|' read -r app_name author git_url instruct_url <<< "$pkg_info"

    echo -e "${GREEN}Package found:${NC} $app_name by $author"
    echo -e "${BLUE}Downloading installation script (.instruct)...${NC}"
    
    local temp_instruct_file
    temp_instruct_file=$(mktemp /tmp/osi-XXXXXX.instruct)
    
    if ! curl -fsSL -o "$temp_instruct_file" "$instruct_url"; then
        echo -e "${RED}Error: Unable to download the .instruct file (HTTP status error or network timeout).${NC}"
        echo -e "${YELLOW}Target URL: $instruct_url${NC}"
        rm -f "$temp_instruct_file"
        exit 1
    fi

    if [ ! -s "$temp_instruct_file" ] || grep -q -i -E "(<html|too many requests|rate limit|404: not found|403: forbidden|error)" "$temp_instruct_file" 2>/dev/null; then
        echo -e "${RED}Error: Downloaded .instruct file is empty, invalid, or blocked by a rate limit/firewall (HTTP 429).${NC}"
        echo -e "${YELLOW}Please inspect the URL directly or try again later: $instruct_url${NC}"
        echo -e "${CYAN}--- File Contents ---${NC}"
        head -n 5 "$temp_instruct_file" 2>/dev/null || true
        echo -e "${CYAN}---------------------${NC}"
        rm -f "$temp_instruct_file"
        exit 1
    fi

    # Parsing headers of .instruct file
    local header_app_name=""
    local header_author=""
    local header_git_url=""
    local header_supported_bases=""
    local header_required_pms=""
    local header_dependencies=""
    local header_allow_clone_deletion="true"

    # Separate config variables from raw build actions
    local is_command_section=false
    local commands_temp_file
    commands_temp_file=$(mktemp /tmp/osi-commands-XXXXXX.txt)

    while IFS= read -r line || [ -n "$line" ]; do
        line=$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        [ -z "$line" ] && continue

        if [ "$is_command_section" = false ]; then
            if [[ "$line" =~ ^([a-zA-Z0-9_-]+)[[:space:]]*=[[:space:]]*(.*)$ ]]; then
                key="${BASH_REMATCH[1]}"
                value="${BASH_REMATCH[2]}"
                
                case "$key" in
                    "app-name") header_app_name="$value" ;;
                    "author") header_author="$value" ;;
                    "git-url") header_git_url="$value" ;;
                    "supported-system-base") header_supported_bases="$value" ;;
                    "required-pms") header_required_pms="$value" ;;
                    "required-dependencies") header_dependencies="$value" ;;
                    "allow-clone-deletion"|"allow-pull-deletion") header_allow_clone_deletion="$value" ;;
                esac
            else
                is_command_section=true
                echo "$line" >> "$commands_temp_file"
            fi
        else
            echo "$line" >> "$commands_temp_file"
        fi
    done < "$temp_instruct_file"

    [ -z "$header_app_name" ] && header_app_name="$app_name"
    [ -z "$header_git_url" ] && header_git_url="$git_url"
    [ -z "$header_author" ] && header_author="$author"

    echo -e "${BLUE}Validating target platform compatibility...${NC}"
    detect_system_base
    
    if [ -n "$header_supported_bases" ]; then
        local compatible=false
        IFS=',' read -ra bases <<< "$header_supported_bases"
        for base in "${bases[@]}"; do
            base_trimmed=$(echo "$base" | xargs)
            if [ "$base_trimmed" = "$SYSTEM_BASE" ] || [ "$base_trimmed" = "all" ]; then
                compatible=true
                break
            fi
        done
        if [ "$compatible" = false ]; then
            echo -e "${RED}Error: This package only supports system bases: $header_supported_bases.${NC}"
            echo -e "Your detected system base is: $SYSTEM_BASE"
            rm -f "$temp_instruct_file" "$commands_temp_file"
            exit 1
        fi
    fi

    # Auto-resolve specialized Package Managers
    if [ -n "$header_required_pms" ]; then
        IFS=',' read -ra pms <<< "$header_required_pms"
        local pm_needs_install=()
        for pm in "${pms[@]}"; do
            pm_trimmed=$(echo "$pm" | xargs)
            [ -z "$pm_trimmed" ] && continue
            if [ "$pm_trimmed" = "system" ]; then
                continue
            fi
            if ! command -v "$pm_trimmed" &> /dev/null; then
                pm_needs_install+=("$pm_trimmed")
            fi
        done

        if [ ${#pm_needs_install[@]} -ne 0 ]; then
            echo -e "${YELLOW}This installation requires specialized package managers: ${pm_needs_install[*]}${NC}"
            if prompt_yes_no "Required package manager(s) [${pm_needs_install[*]}] are missing. Install them?"; then
                echo -e "Installing missing package manager(s) using native package manager ($SYSTEM_PM)..."
                case "$SYSTEM_BASE" in
                    debian) sudo apt-get update && sudo apt-get install -y "${pm_needs_install[@]}" ;;
                    redhat) sudo dnf install -y "${pm_needs_install[@]}" ;;
                    arch) sudo pacman -S --noconfirm "${pm_needs_install[@]}" ;;
                    *) echo -e "${RED}Cannot auto-install missing package managers on unknown system.${NC}"; exit 1 ;;
                esac
            else
                echo -e "${RED}Installation halted due to missing package manager(s).${NC}"
                rm -f "$temp_instruct_file" "$commands_temp_file"
                exit 1
            fi
        fi
    fi

    # Auto-resolve dependencies
    if [ -n "$header_dependencies" ] && [ "$header_dependencies" != "dependencies" ]; then
        echo -e "${BLUE}The package requires the following dependencies: ${YELLOW}$header_dependencies${NC}"
        if prompt_yes_no "Allow OSI to install dependencies using system package manager ($SYSTEM_PM)?"; then
            IFS=',' read -ra deps <<< "$header_dependencies"
            local dep_list=()
            for dep in "${deps[@]}"; do
                dep_list+=("$(echo "$dep" | xargs)")
            done
            
            echo -e "Installing dependencies: ${dep_list[*]}..."
            case "$SYSTEM_BASE" in
                debian)
                    sudo apt-get update && sudo apt-get install -y "${dep_list[@]}"
                    ;;
                redhat)
                    sudo dnf install -y "${dep_list[@]}"
                    ;;
                arch)
                    sudo pacman -Sy --noconfirm "${dep_list[@]}"
                    ;;
                *)
                    echo -e "${YELLOW}Warning: Unknown system base. Please ensure manual installation of: ${dep_list[*]}${NC}"
                    ;;
            esac
        else
            echo -e "${YELLOW}Warning: Skipping dependencies. The build may fail if dependencies are missing.${NC}"
        fi
    fi

    local working_dir
    working_dir=$(pwd)
    local clone_dir=""

    if [ -n "$header_git_url" ] && [ "$header_git_url" != "https://github.com/Dev/Program" ] && [ "$header_git_url" != "None" ]; then
        clone_dir="/tmp/osi-build/$header_app_name"
        echo -e "${BLUE}Cloning source repository from $header_git_url into $clone_dir...${NC}"
        rm -rf "$clone_dir"
        mkdir -p "/tmp/osi-build"
        
        if git clone "$header_git_url" "$clone_dir"; then
            cd "$clone_dir"
        else
            echo -e "${RED}Error: Failed to clone repository.${NC}"
            rm -f "$temp_instruct_file" "$commands_temp_file"
            exit 1
        fi
    else
        clone_dir="/tmp/osi-build/$header_app_name"
        mkdir -p "$clone_dir"
        cd "$clone_dir"
    fi

    echo -e "${BLUE}Executing build/installation commands...${NC}"
    while IFS= read -r cmd || [ -n "$cmd" ]; do
        cmd=$(echo "$cmd" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        [ -z "$cmd" ] && continue
        
        if [ "$cmd" = "[exit]" ]; then
            echo -e "${GREEN}Exit flag detected in instruct script. Terminating installation pipeline.${NC}"
            break
        fi

        echo -e "${CYAN}Executing: $cmd${NC}"
        
        if [[ "$cmd" =~ ^cd[[:space:]]+(.*)$ ]]; then
            eval "cd ${BASH_REMATCH[1]}"
        else
            if ! eval "$cmd"; then
                echo -e "${RED}Error: Command failed to execute: '$cmd'${NC}"
                echo -e "${RED}Aborting installer process.${NC}"
                cd "$working_dir"
                rm -f "$temp_instruct_file" "$commands_temp_file"
                exit 1
            fi
        fi
    done < "$commands_temp_file"

    cd "$working_dir"

    local install_date
    install_date=$(date '+%Y-%m-%d %H:%M:%S')
    local final_location="$clone_dir"
    
    if [ -d "$HOME/Applications/$header_app_name" ]; then
        final_location="$HOME/Applications/$header_app_name"
    elif [ -d "/opt/$header_app_name" ]; then
        final_location="/opt/$header_app_name"
    fi

    # Append registry entry via JQ replacing old if present
    jq --arg n "$header_app_name" --arg a "$header_author" --arg g "$header_git_url" --arg p "$final_location" --arg d "$install_date" 'map(select(.name != $n)) + [{"name": $n, "author": $a, "git_url": $g, "install_path": $p, "install_date": $d}]' "$INSTALLED_REGISTRY" > "${INSTALLED_REGISTRY}.tmp" && mv "${INSTALLED_REGISTRY}.tmp" "$INSTALLED_REGISTRY"

    if [ -n "$SUDO_USER" ]; then
        chown "$SUDO_USER" "$INSTALLED_REGISTRY" 2>/dev/null || true
    fi

    if [ "$header_allow_clone_deletion" = "true" ]; then
        echo -e "${BLUE}Cleaning up source build artifacts (${clone_dir})...${NC}"
        rm -rf "$clone_dir"
    else
        echo -e "${YELLOW}Preserving source repository in: ${clone_dir}${NC}"
    fi

    rm -f "$temp_instruct_file" "$commands_temp_file"
    echo -e "${GREEN}Successfully installed '$header_app_name'!${NC}\n"
}

# Main routing entry
main() {
    check_prerequisites

    local command="$1"
    case "$command" in
        "install")
            if [ "$EUID" -ne 0 ]; then
                echo -e "${YELLOW}OSI requires root permissions to install packages. Elevating...${NC}"
                exec sudo -E "$0" "$@"
            fi
            sync_database
            install_package "$2"
            ;;
        "search")
            sync_database
            search_package "$2"
            ;;
        "remove")
            if [ "$EUID" -ne 0 ]; then
                echo -e "${YELLOW}OSI requires root permissions to remove packages. Elevating...${NC}"
                exec sudo -E "$0" "$@"
            fi
            remove_package "$2"
            ;;
        "list")
            list_installed
            ;;
        "help"|"--help"|"-h"|"")
            show_help
            ;;
        *)
            echo -e "${RED}Unknown command: '$command'${NC}"
            show_help
            exit 1
            ;;
    esac
}

# Run program
main "$@"