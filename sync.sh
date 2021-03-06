#!/bin/bash

if [ "$1" == "setup" ] ; then
	echo "Installing virtualenv package..."
	pip install virtualenv

	echo "Creating virtual environment..."
	virtualenv .	

	if [ "$?" -eq 0 ] ; then
		echo "Activating environment..."
		source bin/activate
		
		echo "Installing pip requirements..."
		pip install -r requirements.txt

		if [ "$?" -eq 0 ] ; then
		  echo "Your environment is ready!"
		fi

	else
		echo "There was a problem creating your virtual environment :("
		exit 1
	fi
else
	echo "Activating environment..."
	source bin/activate

	# Run the script
	python ./code/main.py "$@"
fi



