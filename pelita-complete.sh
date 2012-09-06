PELITADIR=$(pwd)

_pelitagame()
{
  _init_completion || return
  COMPREPLY=( $( compgen -W '$( $PELITADIR/pelitagame --print-args )' -- "$cur" ) )
} && complete -F _pelitagame pelitagame

