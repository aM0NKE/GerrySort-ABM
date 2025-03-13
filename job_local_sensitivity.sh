#!/bin/bash
#SBATCH --exclusive
#SBATCH --time=01:30:00
#SBATCH -N 2
#SBATCH --ntasks-per-node=16

source ~/miniconda3/bin/activate gerrysort

mpirun python3 runMPI_local_sensitivity.py