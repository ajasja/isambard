#ISAMBARD
###Intelligent System for Analysis, Model Building And Rational Design of proteins.
#### Version 0.4.0 (June 23, 2016), Woolfson Group, University of Bristol.
[![CircleCI](https://circleci.com/gh/woolfson-group/isambard_dev.svg?style=svg)](https://circleci.com/gh/woolfson-group/isambard_dev)
[![CircleCI](https://circleci.com/gh/woolfson-group/isambard.svg?style=shield&circle-token=27387ac82a6d30c7bd6a72ce3214fa57677e9d87)](https://circleci.com/gh/woolfson-group/isambar
[![Gitter](https://img.shields.io/gitter/room/nwjs/nw.js.svg?maxAge=2592000)](https://gitter.im/woolfson-group/isambard?utm_source=share-link&utm_medium=link&utm_campaign=share-link)
[![MIT licensed](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/woolfson-group/isambard/blob/master/LICENSE.md)

## Recent Changes
#### v0.4.0
* Loop Closure Functionality
    * Functions for performing kinematic closure of loops have now been added to `isambard.ampal.loops`
    * This module uses Metropolis Monte Carlo backbone moves to fit a loop between two regions of protein
    * The major function is `isambard.loops.fit_loop_between`
* `join` method has now been separated into `n_join` and `c_join`
* Socket
    * Socket functionality is now completely replicated using native ISAMBARD code
    * The Socket external dependency has been removed

#### v0.3.1
* New PDB Parser
    * Much more robust
    * Allows preprocessing of the PDB file
    * Easy to add filters to the parsering of the PDB and the generation of the AMPAL object
* Automatic configuration script `configure.py` added
    * This generates the settings.json file using user information
    * Use `python configure.py` to run
    * Add the `-o` flag if you have existing settings you wish to overwrite
* `settings.json` has a new general format
* [CircleCI](https://circleci.com/) has been linked to the ISAMBARD repository
    * This is a tool for [continuous integration](https://en.wikipedia.org/wiki/Continuous_integration)
    * Whenever changes are pushed to master CircleCI downloads ISAMBARD and runs the unit tests
    * There is a badge in the `README.md` detailing the current CircleCI status 

[**See full change log**](https://github.com/woolfson-group/isambard/wiki/Change-Log)

##Principal Investigator
Derek N. Woolfson (d.n.woolfson@bristol.ac.uk)
##Developers
###Core Dev Team
####Woolfson Group
Gail J. Bartlett (g.bartlett@bristol.ac.uk)<br>
Jack W. Heal (jack.heal@bristol.ac.uk)<br>
Kieran L. Hudson (kieran.hudson@bristol.ac.uk)<br>
Andrew R. Thomson (drew.thomson@bristol.ac.uk)<br>
Christopher W. Wood (chris.wood@bristol.ac.uk)<br>
###Contributors
####Woolfson Group
Caitlin Edgell<br>
Kathryn L. Porter Goff<br>
###BUDE Dev Team
####Sessions Group
Amaurys À. Ibarra (amaurys.avilaibarra@bristol.ac.uk)<br>
Richard B. Sessions (r.sessions@bristol.ac.uk)<br>
