import os
import sys
import subprocess
from typing import Tuple, Optional

START_MARKER = "# === AEGIS PROTECTION BOUNDARY START ==="
END_MARKER = "# === AEGIS PROTECTION BOUNDARY END ==="

PROFILE_SCRIPT_TEMPLATE = r"""# === AEGIS PROTECTION BOUNDARY START ===
function Invoke-AegisPreExecutionBoundary {
    try {
        $cmdArgs = [System.Environment]::GetCommandLineArgs()
        if ($null -eq $cmdArgs -or $cmdArgs.Length -le 1) {
            # Interactive shell startup without execution arguments
            return
        }

        $targetCmd = $null
        $foundInvocationFlag = $false

        for ($i = 1; $i -lt $cmdArgs.Length; $i++) {
            $arg = $cmdArgs[$i]
            
            # 1. -Command or -c
            if ($arg -ieq "-Command" -or $arg -ieq "-c") {
                $foundInvocationFlag = $true
                if (($i + 1) -lt $cmdArgs.Length) {
                    $targetCmd = $cmdArgs[$i + 1]
                } else {
                    [System.Console]::ForegroundColor = [System.ConsoleColor]::Red
                    [System.Console]::WriteLine("[Aegis Supervision] AEGIS PROTECTION ERROR: Missing argument for -Command flag. Failing closed.")
                    [System.Console]::ResetColor()
                    [System.Environment]::Exit(3)
                }
                break
            }
            # 2. -Command:<val> or -c:<val>
            elseif ($arg -imatch "^-(Command|c):(.*)$") {
                $foundInvocationFlag = $true
                $targetCmd = $Matches[2]
                break
            }
            # 3. -EncodedCommand, -e, -ec
            elseif ($arg -ieq "-EncodedCommand" -or $arg -ieq "-e" -or $arg -ieq "-ec") {
                $foundInvocationFlag = $true
                if (($i + 1) -lt $cmdArgs.Length) {
                    $encodedStr = $cmdArgs[$i + 1]
                    try {
                        $bytes = [System.Convert]::FromBase64String($encodedStr)
                        $targetCmd = [System.Text.Encoding]::Unicode.GetString($bytes)
                    } catch {
                        [System.Console]::ForegroundColor = [System.ConsoleColor]::Red
                        [System.Console]::WriteLine("[Aegis Supervision] AEGIS PROTECTION ERROR: Invalid Base64 in -EncodedCommand. Failing closed.")
                        [System.Console]::ResetColor()
                        [System.Environment]::Exit(3)
                    }
                } else {
                    [System.Console]::ForegroundColor = [System.ConsoleColor]::Red
                    [System.Console]::WriteLine("[Aegis Supervision] AEGIS PROTECTION ERROR: Missing argument for -EncodedCommand flag. Failing closed.")
                    [System.Console]::ResetColor()
                    [System.Environment]::Exit(3)
                }
                break
            }
            # 4. -EncodedCommand:<val>, -e:<val>, -ec:<val>
            elseif ($arg -imatch "^-(EncodedCommand|e|ec):(.*)$") {
                $foundInvocationFlag = $true
                $encodedStr = $Matches[2]
                try {
                    $bytes = [System.Convert]::FromBase64String($encodedStr)
                    $targetCmd = [System.Text.Encoding]::Unicode.GetString($bytes)
                } catch {
                    [System.Console]::ForegroundColor = [System.ConsoleColor]::Red
                    [System.Console]::WriteLine("[Aegis Supervision] AEGIS PROTECTION ERROR: Invalid Base64 in -EncodedCommand. Failing closed.")
                    [System.Console]::ResetColor()
                    [System.Environment]::Exit(3)
                }
                break
            }
            # 5. -File or -f
            elseif ($arg -ieq "-File" -or $arg -ieq "-f") {
                $foundInvocationFlag = $true
                if (($i + 1) -lt $cmdArgs.Length) {
                    $filePath = $cmdArgs[$i + 1]
                    $remainingArgs = ""
                    if (($i + 2) -lt $cmdArgs.Length) {
                        $remainingArgs = " " + ($cmdArgs[($i + 2)..($cmdArgs.Length - 1)] -join " ")
                    }
                    $targetCmd = "$filePath$remainingArgs".Trim()
                } else {
                    [System.Console]::ForegroundColor = [System.ConsoleColor]::Red
                    [System.Console]::WriteLine("[Aegis Supervision] AEGIS PROTECTION ERROR: Missing argument for -File flag. Failing closed.")
                    [System.Console]::ResetColor()
                    [System.Environment]::Exit(3)
                }
                break
            }
            # 6. -File:<val> or -f:<val>
            elseif ($arg -imatch "^-(File|f):(.*)$") {
                $foundInvocationFlag = $true
                $filePath = $Matches[2]
                $remainingArgs = ""
                if (($i + 1) -lt $cmdArgs.Length) {
                    $remainingArgs = " " + ($cmdArgs[($i + 1)..($cmdArgs.Length - 1)] -join " ")
                }
                $targetCmd = "$filePath$remainingArgs".Trim()
                break
            }
        }

        if (-not $foundInvocationFlag) {
            # No recognized target command flag found in command-line arguments.
            # Normal interactive session startup returns silently.
            return
        }

        if ([string]::IsNullOrWhiteSpace($targetCmd) -or $targetCmd -eq "exit") {
            return
        }

        # Check explicit Protection State (OFF => passthrough normal operation without requiring Gateway)
        $stateFile = Join-Path (Get-Location).Path "config\protection_state.json"
        if (-not (Test-Path $stateFile) -and $env:AEGIS_WORKSPACE_ROOT) {
            $stateFile = Join-Path $env:AEGIS_WORKSPACE_ROOT "config\protection_state.json"
        }
        if (Test-Path $stateFile) {
            try {
                $stateContent = Get-Content $stateFile -Raw | ConvertFrom-Json
                if ($stateContent.enabled -eq $false -or $stateContent.status -eq "OFF") {
                    # Protection explicitly OFF by human choice => Passthrough
                    return
                }
            } catch { }
        }

        # Query Aegis Gateway Service via HTTP
        $payload = @{
            command = $targetCmd
            cwd = (Get-Location).Path
            session_id = $env:ANTIGRAVITY_TRAJECTORY_ID
            task_id = $env:ANTIGRAVITY_AGENT
        } | ConvertTo-Json -Compress

        $gatewayUrl = "http://127.0.0.1:8765/evaluate"
        $response = $null
        try {
            $req = [System.Net.HttpWebRequest]::Create($gatewayUrl)
            $req.Method = "POST"
            $req.ContentType = "application/json"
            $req.Timeout = 10000
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
            $req.ContentLength = $bytes.Length
            $stream = $req.GetRequestStream()
            $stream.Write($bytes, 0, $bytes.Length)
            $stream.Close()

            $res = $req.GetResponse()
            $reader = [System.IO.StreamReader]::new($res.GetResponseStream())
            $jsonStr = $reader.ReadToEnd()
            $response = $jsonStr | ConvertFrom-Json
        } catch [System.Net.WebException] {
            $webRes = $_.Exception.Response
            if ($null -ne $webRes) {
                try {
                    $reader = [System.IO.StreamReader]::new($webRes.GetResponseStream())
                    $jsonStr = $reader.ReadToEnd()
                    $response = $jsonStr | ConvertFrom-Json
                } catch { }
            }
        } catch { }

        if ($null -eq $response) {
            # Gateway offline / error / unreachable -> FAIL CLOSED
            [System.Console]::ForegroundColor = [System.ConsoleColor]::Red
            [System.Console]::WriteLine("[Aegis Supervision] AEGIS GATEWAY UNAVAILABLE - FAILING CLOSED")
            [System.Console]::ResetColor()
            [System.Console]::WriteLine("Error: Gateway could not evaluate command. Execution blocked for security.")
            [System.Environment]::Exit(3)
        }

        $gwStatus = $response.gateway_status
        if ($gwStatus -eq "PERMITTED" -or $gwStatus -eq "PASSTHROUGH") {
            return
        } elseif ($gwStatus -eq "PAUSED_FOR_APPROVAL") {
            [System.Console]::ForegroundColor = [System.ConsoleColor]::Yellow
            [System.Console]::WriteLine("[Aegis Supervision] RISKY COMMAND PAUSED FOR HUMAN APPROVAL")
            [System.Console]::ResetColor()
            [System.Console]::WriteLine("Command:     $($response.command)")
            [System.Console]::WriteLine("Request ID:  $($response.approval_id)")
            [System.Console]::WriteLine("Reason:      $($response.explanation)")
            [System.Console]::WriteLine("To approve:  python main.py --approve $($response.approval_id)")
            [System.Console]::WriteLine("To deny:     python main.py --deny $($response.approval_id)")
            [System.Environment]::Exit(2)
        } else {
            [System.Console]::ForegroundColor = [System.ConsoleColor]::Red
            [System.Console]::WriteLine("[Aegis Supervision] CRITICAL COMMAND BLOCKED BY AEGIS POLICY")
            [System.Console]::ResetColor()
            [System.Console]::WriteLine("Command:     $($response.command)")
            [System.Console]::WriteLine("Reason:      $($response.explanation)")
            [System.Environment]::Exit(1)
        }
    } catch {
        [System.Console]::ForegroundColor = [System.ConsoleColor]::Red
        [System.Console]::WriteLine("[Aegis Supervision] AEGIS INTERCEPTION ERROR - FAILING CLOSED")
        [System.Console]::ResetColor()
        [System.Console]::WriteLine("Error: $_")
        [System.Environment]::Exit(3)
    }
}
Invoke-AegisPreExecutionBoundary
# === AEGIS PROTECTION BOUNDARY END ===
"""


class ProfileInstaller:
    """Manages installation and removal of Aegis PowerShell profile pre-execution interceptor."""

    @staticmethod
    def get_profile_path() -> Optional[str]:
        try:
            res = subprocess.run(
                ["powershell", "-Command", "Get-Variable PROFILE | Select-Object -ExpandProperty Value"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            path = res.stdout.strip()
            if path and not path.startswith("Error"):
                return path
        except Exception:
            pass

        # Fallback standard Windows PowerShell profile paths
        user_home = os.path.expanduser("~")
        onedrive_path = os.path.join(user_home, "OneDrive", "Documents", "WindowsPowerShell", "Microsoft.PowerShell_profile.ps1")
        if os.path.exists(onedrive_path):
            return onedrive_path

        docs_path = os.path.join(user_home, "Documents", "WindowsPowerShell", "Microsoft.PowerShell_profile.ps1")
        return docs_path

    @classmethod
    def is_installed(cls, profile_path: Optional[str] = None) -> bool:
        path = profile_path or cls.get_profile_path()
        if not path or not os.path.exists(path):
            return False
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return START_MARKER in content and END_MARKER in content

    @classmethod
    def install(cls, profile_path: Optional[str] = None) -> Tuple[bool, str]:
        path = profile_path or cls.get_profile_path()
        if not path:
            return False, "Could not determine PowerShell profile path."

        os.makedirs(os.path.dirname(path), exist_ok=True)

        existing_content = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                existing_content = f.read()

        if START_MARKER in existing_content:
            # Strip existing block first before reinstalling
            lines = existing_content.splitlines()
            new_lines = []
            skipping = False
            for line in lines:
                if START_MARKER in line:
                    skipping = True
                    continue
                if END_MARKER in line:
                    skipping = False
                    continue
                if not skipping:
                    new_lines.append(line)
            existing_content = "\n".join(new_lines).strip()

        new_content = (existing_content + "\n\n" if existing_content else "") + PROFILE_SCRIPT_TEMPLATE

        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return True, f"Aegis pre-execution interceptor successfully installed in {path}"

    @classmethod
    def uninstall(cls, profile_path: Optional[str] = None) -> Tuple[bool, str]:
        path = profile_path or cls.get_profile_path()
        if not path or not os.path.exists(path):
            return False, "Profile file does not exist."

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if START_MARKER not in content:
            return True, "Aegis interceptor is not installed in profile."

        lines = content.splitlines()
        new_lines = []
        skipping = False
        for line in lines:
            if START_MARKER in line:
                skipping = True
                continue
            if END_MARKER in line:
                skipping = False
                continue
            if not skipping:
                new_lines.append(line)

        cleaned = "\n".join(new_lines).strip()
        with open(path, "w", encoding="utf-8") as f:
            f.write(cleaned + "\n" if cleaned else "")

        return True, f"Aegis pre-execution interceptor successfully removed from {path}"
