import os
import sys
from typing import NoReturn

import colorama

from covert.cli import main_benchmark, main_dec, main_edit, main_enc, main_id
from covert.clihelp import print_help, print_version


class Args:

  def __init__(self):
    self.mode = None
    self.idname = ""
    self.files = []
    self.wideopen = None
    self.askpass = 0
    self.passwords = []
    self.recipients = []
    self.recipfiles = []
    self.outfile = []
    self.identities = []
    self.padding = "5"
    self.armor = None
    self.paste = None
    self.debug = None
    self.delete_entire_idstore = False
    self.delete = False
    self.secret = False


encargs = dict(
  idname='-I --id'.split(),
  askpass='-p --passphrase'.split(),
  passwords='--password'.split(),
  wideopen='--wide-open'.split(),
  recipients='-r --recipient'.split(),
  recipfiles='-R --keyfile --recipients-file'.split(),
  identities='-i --identity'.split(),
  outfile='-o --out --output'.split(),
  armor='-a --armor'.split(),
  paste='-A'.split(),
  padding='--pad --padding'.split(),
  debug='--debug'.split(),
)

decargs = dict(
  idname='-I --id'.split(),
  askpass='-p --passphrase'.split(),
  passwords='--password'.split(),
  identities='-i --identity'.split(),
  outfile='-o --out --output'.split(),
  paste='-A'.split(),
  debug='--debug'.split(),
)

idargs = dict(
  askpass='-p --passphrase'.split(),
  recipients='-r --recipient'.split(),
  recipfiles='-R --keyfile --recipients-file'.split(),
  identities='-i --identity'.split(),
  secret='-s --secret'.split(),
  delete_entire_idstore='--delete-entire-idstore'.split(),
  delete='-D --delete'.split(),
  debug='--debug'.split(),
)

editargs = dict(debug='--debug'.split(),)
benchargs = dict(debug='--debug'.split(),)

# TODO: Put mode args and help here as well
modes = {
  "enc": main_enc,
  "dec": main_dec,
  "edit": main_edit,
  "id": main_id,
  "benchmark": main_benchmark,
}

def needhelp(av):
  """Check for -h and --help but not past --"""
  for a in av:
    if a == '--': return False
    if a.lower() in ('-h', '--help'): return True
  return False

def subcommand(arg):
  if arg in ('enc', 'encrypt', '-e'): return 'enc', encargs
  if arg in ('dec', 'decrypt', '-d'): return 'dec', decargs
  if arg in ('edit'): return 'edit', editargs
  if arg in ('id'): return 'id', idargs
  if arg in ('bench', 'benchmark'): return 'benchmark', benchargs
  if arg in ('help', ): return 'help', {}
  return None, {}

def argparse():
  # Custom parsing due to argparse module's limitations
  av = sys.argv[1:]
  if not av:
    print_help()

  if any(a.lower() in ('-v', '--version') for a in av):
    print_version()

  args = Args()
  # Separate mode selector from other arguments
  if av[0].startswith("-") and len(av[0]) > 2 and not needhelp(av):
      av.insert(1, f'-{av[0][2:]}')
      av[0] = av[0][:2]

  args.mode, ad = subcommand(av[0])

  if args.mode == 'help' or needhelp(av):
    if args.mode == 'help' and len(av) == 2 and (mode := subcommand(av[1])[0]):
      print_help(mode)
    print_help(args.mode or "help")

  if args.mode is None:
    sys.stderr.write(' 💣  Invalid or missing command (enc/dec/edit/id/benchmark/help).\n')
    sys.exit(1)

  aiter = iter(av[1:])
  longargs = [flag[1:] for switches in ad.values() for flag in switches if flag.startswith("--")]
  shortargs = [flag[1:] for switches in ad.values() for flag in switches if not flag.startswith("--")]
  for a in aiter:
    aprint = a
    if not a.startswith('-'):
      args.files.append(a)
      continue
    if a == '-':
      args.files.append(True)
      continue
    if a == '--':
      args.files += aiter
      break
    if a.startswith('--'):
      a = a.lower()
    if not a.startswith('--') and len(a) > 2:
      if any(arg not in shortargs for arg in list(a[1:])):
        falseargs = [arg for arg in list(a[1:]) if arg not in shortargs]
        print_help(args.mode, f' 💣  Unknown argument: covert {args.mode} {a} (failing -{" -".join(falseargs)})')
      a = [f'-{shortarg}' for shortarg in list(a[1:]) if shortarg in shortargs]
    if isinstance(a, str):
      a = [a]
    for i, av in enumerate(a):
      argvar = next((k for k, v in ad.items() if av in v), None)
      if isinstance(av, int):
        continue
      if argvar is None:
        print_help(args.mode, f' 💣  Unknown argument: covert {args.mode} {aprint}')
      try:
        var = getattr(args, argvar)
        if isinstance(var, list):
          var.append(next(aiter))
        elif isinstance(var, str):
          setattr(args, argvar, next(aiter))
        elif isinstance(var, int):
          setattr(args, argvar, var + 1)
        else:
          setattr(args, argvar, True)
      except StopIteration:
        print_help(args.mode, f' 💣  Argument parameter missing: covert {args.mode} {aprint} …')

  return args


def main() -> NoReturn:
  """
  The main CLI entry point.

  Consider calling covert.cli.main* or other modules directly if you use from Python code.

  System exit codes:
  * 0 The requested function was completed successfully
  * 1 CLI argument error
  * 2 I/O error (broken pipe, not other types currently)
  * 10-99 Normal errors, authentication failures, corrupted data, ... (currently 10 for all)

  :raises SystemExit: on normal exit or any expected error, including KeyboardInterrupt
  :raises Exception: on unexpected error (report a bug), or on any error with `--debug`
  """
  colorama.init()
  # CLI argument processing
  args = argparse()
  if len(args.outfile) > 1:
    raise ValueError('Only one output file may be specified')
  args.outfile = args.outfile[0] if args.outfile else None

  # A quick sanity check, not entirely reliable
  if args.outfile in args.files:
    raise ValueError('In-place operation is not supported, cannot use the same file as input and output.')

  # Run the mode-specific main function
  if args.debug:
    modes[args.mode](args)  # --debug makes us not catch errors
    sys.exit(0)
  try:
    modes[args.mode](args)  # Normal run
  except ValueError as e:
    sys.stderr.write(f"Error: {e}\n")
    sys.exit(10)
  except BrokenPipeError:
    sys.stderr.write('I/O error (broken pipe)\n')
    sys.exit(3)
  except KeyboardInterrupt:
    sys.stderr.write("Interrupted.\n")
    sys.exit(2)
  sys.exit(0)

if __name__ == "__main__":
  main()
