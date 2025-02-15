# -*- mode: python -*-
# virtme-configkernel: Configure a kernel for virtme
# Copyright © 2014 Andy Lutomirski
# Licensed under the GPLv2, which is available in the virtme distribution
# as a file called LICENSE with SHA-256 hash:
# 8177f97513213526df2cf6184d8ff986c675afb514d4e68a404010521b880643

from typing import Optional

import argparse
import os
import shlex
import shutil
import subprocess
import multiprocessing
from .. import architectures

uname = os.uname()

def make_parser():
    parser = argparse.ArgumentParser(
        description='Configure a kernel for virtme',
    )

    parser.add_argument('--arch', action='store', metavar='ARCHITECTURE',
                        default=uname.machine,
                        help='Target architecture')

    parser.add_argument('--custom', action='append', metavar='CUSTOM',
                        help='Use a custom config snippet file to override specific config options')

    g = parser.add_argument_group(title='Mode').add_mutually_exclusive_group()

    g.add_argument('--allnoconfig', action='store_true',
                        help='Overwrite configuration with a virtme-suitable allnoconfig (unlikely to work)')

    g.add_argument('--defconfig', action='store_true',
                        help='Overwrite configuration with a virtme-suitable defconfig')

    g.add_argument('--update', action='store_true',
                        help='Update existing config for virtme')

    parser.add_argument('envs', metavar='envs', type=str, nargs='*',
                        help='Additional Makefile variables')

    return parser

_ARGPARSER = make_parser()

def arg_fail(message):
    print(message)
    _ARGPARSER.print_usage()
    exit(1)

_GENERIC_CONFIG = [
    '# Generic',
    'CONFIG_UEVENT_HELPER=n',	# Obsolete and slow
    'CONFIG_VIRTIO=y',
    'CONFIG_VIRTIO_PCI=y',
    'CONFIG_VIRTIO_MMIO=y',
    'CONFIG_NET=y',
    'CONFIG_NET_CORE=y',
    'CONFIG_NETDEVICES=y',
    'CONFIG_NETWORK_FILESYSTEMS=y',
    'CONFIG_INET=y',
    'CONFIG_NET_9P=y',
    'CONFIG_NET_9P_VIRTIO=y',
    'CONFIG_9P_FS=y',
    'CONFIG_VIRTIO_NET=y',
    'CONFIG_CMDLINE_OVERRIDE=n',
    'CONFIG_BINFMT_SCRIPT=y',
    'CONFIG_SHMEM=y',
    'CONFIG_TMPFS=y',
    'CONFIG_UNIX=y',
    'CONFIG_MODULE_SIG_FORCE=n',
    'CONFIG_DEVTMPFS=y',
    'CONFIG_TTY=y',
    'CONFIG_VT=y',
    'CONFIG_UNIX98_PTYS=y',
    'CONFIG_EARLY_PRINTK=y',
    'CONFIG_INOTIFY_USER=y',
    '',
    '# virtio-scsi support',
    'CONFIG_BLOCK=y',
    'CONFIG_SCSI_LOWLEVEL=y',
    'CONFIG_SCSI=y',
    'CONFIG_SCSI_VIRTIO=y',
    'CONFIG_BLK_DEV_SD=y',
    '',
    '# virt-serial support',
    'CONFIG_VIRTIO_CONSOLE=y',
    '',
    '# watchdog (useful for test scripts)',
    'CONFIG_WATCHDOG=y',
    'CONFIG_WATCHDOG_CORE=y',
    'CONFIG_I6300ESB_WDT=y',

    '# Make sure debuginfo are available',
    'CONFIG_DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT=y',

    '# Enable overlayfs',
    'CONFIG_OVERLAY_FS=y',
]

_GENERIC_CONFIG_OPTIONAL = [
    '# initramfs support',
    'BLK_DEV_INITRD=y',

    '# Provide USB support as module',
    'CONFIG_USB=m'

    '# BPF stuff',
    'CONFIG_BPF=y',
    'CONFIG_BPF_SYSCALL=y',
    'CONFIG_BPF_JIT=y',
    'CONFIG_HAVE_EBPF_JIT=y',
    'CONFIG_BPF_EVENTS=y',
    'CONFIG_FTRACE_SYSCALLS=y',
    'CONFIG_FUNCTION_TRACER=y',
    'CONFIG_HAVE_DYNAMIC_FTRACE=y',
    'CONFIG_DYNAMIC_FTRACE=y',
    'CONFIG_HAVE_KPROBES=y',
    'CONFIG_KPROBES=y',
    'CONFIG_KPROBE_EVENTS=y',
    'CONFIG_ARCH_SUPPORTS_UPROBES=y',
    'CONFIG_UPROBES=y',
    'CONFIG_UPROBE_EVENTS=y',
    'CONFIG_DEBUG_FS=y',
    'CONFIG_DEBUG_INFO_BTF=y',

    '# Useful debugging features',
    'CONFIG_PROVE_LOCKING=y',

    '# Unnecessary configs',
    '# CONFIG_LOCALVERSION_AUTO is not set',
    '# CONFIG_DRM is not set',
    '# CONFIG_SOUND is not set',
    '# CONFIG_I2C is not set',
    '# CONFIG_INPUT_MOUSE is not set',
    '# CONFIG_MOUSE_PS2 is not set',
    '# CONFIG_USB_HID is not set',
    '# CONFIG_HID is not set',
    '# CONFIG_TIGON3 is not set',
    '# CONFIG_BNX2X is not set',
    '# CONFIG_CHELSIO_T1 is not set',
    '# CONFIG_BE2NET is not set',
    '# CONFIG_S2IO is not set',
    '# CONFIG_EHEA is not set',
    '# CONFIG_E100 is not set',
    '# CONFIG_IXGB is not set',
    '# CONFIG_IXGBE is not set',
    '# CONFIG_I40E is not set',
    '# CONFIG_MLX4_EN is not set',
    '# CONFIG_MLX5_CORE is not set',
    '# CONFIG_MYRI10GE is not set',
    '# CONFIG_NETXEN_NIC is not set',
    '# CONFIG_NFS_FS is not set',
    '# CONFIG_IPV6 is not set',
    '# CONFIG_AUDIT is not set',
    '# CONFIG_SECURITY is not set',
    '# CONFIG_WIRELESS is not set',
    '# CONFIG_WLAN is not set',
    '# CONFIG_SCHED_MC is not set',
    '# CONFIG_CPU_FREQ is not set',
    '# CONFIG_INFINIBAND is not set',
    '# CONFIG_PPP is not set',
    '# CONFIG_PPPOE is not set',
    '# CONFIG_EXT2_FS is not set',
    '# CONFIG_REISERFS_FS not set',
    '# CONFIG_JFS_FS is not set',
    '# CONFIG_XFS_FS is not set',
    '# CONFIG_BTRFS_FS is not set',
    '# CONFIG_HFS_FS is not set',
    '# CONFIG_HFSPLUS_FS is not set',
    '# CONFIG_SCSI_FC_ATTRS is not set',
    '# CONFIG_SCSI_CXGB3_ISCSI is not set',
    '# CONFIG_SCSI_CXGB4_ISCSI is not set',
    '# CONFIG_SCSI_BNX2_ISCSI is not set',
    '# CONFIG_BE2ISCSI is not set',
    '# CONFIG_SCSI_MPT2SAS is not set',
    '# CONFIG_SCSI_IBMVFC is not set',
    '# CONFIG_SCSI_SYM53C8XX_2 is not set',
    '# CONFIG_SCSI_IPR is not set',
    '# CONFIG_SCSI_QLA_FC is not set',
    '# CONFIG_SCSI_QLA_ISCSI is not set',
    '# CONFIG_SCSI_DH is not set',
    '# CONFIG_FB_MATROX is not set',
    '# CONFIG_FB_RADEON is not set',
    '# CONFIG_FB_IBM_GXT4500 is not set',
]

def main():
    args = _ARGPARSER.parse_args()

    if not os.path.isfile('scripts/kconfig/merge_config.sh') and \
       not os.path.isfile('source/scripts/kconfig/merge_config.sh'):
        print('virtme-configkernel must be run in a kernel source/build directory')
        return 1

    arch = architectures.get(args.arch)

    custom_conf = []
    if args.custom:
        for conf_chunk in args.custom:
            with open(conf_chunk) as fd:
                custom_conf += fd.readlines()

    conf = (_GENERIC_CONFIG_OPTIONAL +
            ['# Arch-specific options'] +
            arch.config_base() +
            custom_conf +
            _GENERIC_CONFIG)

    archargs = ['ARCH=%s' % shlex.quote(arch.linuxname)]

    if shutil.which('%s-linux-gnu-gcc' % arch.gccname):
        archargs.append('CROSS_COMPILE=%s' % shlex.quote("%s-linux-gnu-" % arch.gccname))

    maketarget: Optional[str]

    if args.allnoconfig:
        maketarget = 'allnoconfig'
        updatetarget = 'syncconfig'
    elif args.defconfig:
        maketarget = arch.defconfig_target
        updatetarget = 'olddefconfig'
    elif args.update:
        maketarget = None
        updatetarget = 'olddefconfig'
    else:
        arg_fail('No mode selected')

    # TODO: Get rid of most of the noise and check the result.

    # Set up an initial config
    if maketarget:
        subprocess.check_call(['make'] + archargs + [maketarget])

    config = '.config'

    # Check if KBUILD_OUTPUT is defined and if it's a directory
    config_dir = os.environ.get('KBUILD_OUTPUT', '')
    if config_dir and os.path.isdir(config_dir):
        config = os.path.join(config_dir, config)

    with open(config, 'ab') as conffile:
        conffile.write('\n'.join(conf).encode('utf-8'))

    # Propagate additional Makefile variables
    for var in args.envs:
        archargs.append(shlex.quote(var))

    subprocess.check_call(['make'] + archargs + [updatetarget])

    print("Configured.  Build with 'make %s -j%d'" %
          (' '.join(archargs), multiprocessing.cpu_count()))

    return 0

if __name__ == '__main__':
    exit(main())
