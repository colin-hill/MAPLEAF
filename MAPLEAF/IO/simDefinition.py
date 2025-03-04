# Created by Henry Stoldt
# January 2019

''' 
Contains a class to read, write and modify simulation definition (.mapleaf) files, the master dictionary of 
default values for simulation definitions, and a few utility functions for working with string dictionary keys
'''
import os
import random
import re
import shlex
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Union

from MAPLEAF.Motion import Vector

__all__ = [ "defaultConfigValues", "SimDefinition", "getAbsoluteFilePath" ]

#################### Default value dictionary  #########################
defaultConfigValues = {
    "Optimization.showConvergencePlot":                     "True",

    "MonteCarlo.output":                                    "landingLocations",

    "SimControl.plot":                                      "Position FlightAnimation",
    "SimControl.loggingLevel":                              "2",
    "SimControl.EndCondition":                              "Altitude",
    "SimControl.EndConditionValue":                         "-1",
    "SimControl.StageDropPaths.compute":                    "true",
    "SimControl.StageDropPaths.endCondition":               "Altitude",
    "SimControl.StageDropPaths.endConditionValue":          "0",
    "SimControl.timeDiscretization":                        "RK45Adaptive",
    "SimControl.timeStep":                                  "0.01",
    "SimControl.TimeStepAdaptation.controller":             "PID",
    "SimControl.TimeStepAdaptation.targetError":            "0.001",
    "SimControl.TimeStepAdaptation.minFactor":              "0.3",
    "SimControl.TimeStepAdaptation.maxFactor":              "1.5",
    "SimControl.TimeStepAdaptation.Elementary.safetyFactor":"0.9",
    "SimControl.TimeStepAdaptation.maxTimeStep":            "30",
    "SimControl.TimeStepAdaptation.minTimeStep":            "0.0001",
    "SimControl.TimeStepAdaptation.PID.coefficients":       "-0.01 -0.001 0",
    "SimControl.TimeStepAdaptation.eventTimingAccuracy":    "0.001",
    "SimControl.RocketPlot":                                "Off",

    "Environment.EarthModel":                           "Flat",
    "Environment.AtmosphericPropertiesModel":           "USStandardAtmosphere",
    "Environment.LaunchSite.elevation":                 "0",
    "Environment.LaunchSite.railLength":                "0",
    "Environment.LaunchSite.latitude":                  "0",
    "Environment.LaunchSite.longitude":                 "0",
    "Environment.MeanWindModel":                        "Constant",
    "Environment.ConstantMeanWind.velocity":            "(0 0 0)",
    "Environment.SampledGroundWindData.launchMonth":    "Yearly",
    "Environment.SampledRadioSondeData.launchMonth":    "Yearly",
    "Environment.Hellman.alphaCoeff":                   "0.1429",
    "Environment.Hellman.altitudeLimit":                "1000",
    "Environment.TurbulenceModel":                      "None",
    "Environment.turbulenceOffWhenUnderChute":          "True",

    "Environment.ConstantAtmosphere.temp":              "15",
    "Environment.ConstantAtmosphere.pressure":          "101325",
    "Environment.ConstantAtmosphere.density":           "1.225",
    "Environment.ConstantAtmosphere.viscosity":         "1.789e-5",
    "Environment.TabulatedAtmosphere.filePath":         "MAPLEAF/ENV/US_STANDARD_ATMOSPHERE.txt",
    
    "Rocket.HIL.quatUpdateRate":                        "100",
    "Rocket.HIL.posUpdateRate":                         "20",
    "Rocket.HIL.velUpdateRate":                         "20",
    "Rocket.HIL.teensyComPort":                         "COM20",
    "Rocket.HIL.imuComPort":                            "COM15",
    "Rocket.HIL.teensyBaudrate":                        "9600",
    "Rocket.HIL.imuBaudrate":                           "57600",

    "Rocket.ControlSystem.desiredFlightDirection":      "(0 0 1)",
    "Rocket.ControlSystem.MomentController.Type":       "ScheduledGainPIDRocket",
    "Rocket.ControlSystem.updateRate":                  "0",

    "Rocket.name":                                      "Rocket",
    "Rocket.position":                                  "(0 0 10)",
    "Rocket.initialDirection":                          "(0 0 1)",
    "Rocket.velocity":                                  "(0 0 0)",
    "Rocket.angularVelocity":                           "(0 0 0)",

    "Rocket.Aero.fullyTurbulentBL":                     "true",
    "Rocket.Aero.addZeroLengthBoatTailsToAccountForBaseDrag":"true",
    "Rocket.Aero.surfaceRoughness":                     "0.000005",

    "Stage.stageNumber":                                "0",
    "Stage.separationTriggerType":                      "None",
    "Stage.separationTriggerValue":                     "0",
    "Stage.separationDelay":                            "0",
    "Stage.position":                                   "(0 0 0)",

    "AeroForce.Lref":                                   "0",
    "AeroForce.Cd":                                     "0",
    "AeroForce.Cl":                                     "0",
    "AeroForce.momentCoeffs":                           "(0 0 0)",

    "AeroDamping.zDampingCoeffs":                       "(0 0 0)",
    "AeroDamping.yDampingCoeffs":                       "(0 0 0)",
    "AeroDamping.xDampingCoeffs":                       "(0 0 0)",

    "FinSet.finCantAngle":                              "0",
    "FinSet.firstFinAngle":                             "0",
    "FinSet.LeadingEdge.shape":                         "Round",
    "FinSet.TrailingEdge.shape":                        "Tapered",
    "FinSet.numFinSpanSlicesForIntegration":            "10",

    "Nosecone.shape":                                   "tangentOgive",

    "BoatTail.shape":                                   "cone",

    "Mass.cg":                                          "(0 0 0)",

    "Motor.impulseAdjustFactor":                        "1.0",
    "Motor.burnTimeAdjustFactor":                       "1.0",
    
    "Actuator.controller":                              "TableInterpolating",
    "Actuator.responseModel":                           "FirstOrder",
    "Actuator.responseTime":                            "0.1",

    "RecoverySystem.cg":                                "(0 0 0)",

    "TabulatedAeroForce.Lref":                          "0",
    
    "testValue.testDefaultValue1":                      "asdf",
    "testDefaultValue2":                                "jkl;"
}

simDefinitionHelpMessage = \
"""
    All non-empty, non-comment lines are expected to end in either:
    {   (dictionary start)
    }   (dictionary end)
    
    Or to contain a space-separated key-value pair:
    key value
"""
class SimDefinition():

    #### Parsing / Initialization ####
    def __init__(self, fileName=None, dictionary=None, disableDistributionSampling=False, silent=False, defaultDict=None, simDefParseStack=None):
        '''
        Parse simulation definition files into a dictionary of string values accessible by string keys.

        Inputs:
            * fileName: (str) path to simulation definition file
            * dictionary: (dict[str,str]) Provide a pre-parsed dictionary equivalent to a simulation definition file - OVERRIDES fileName
            
            * disableDistributionSampling: (bool) Turn Monte Carlo sampling of normally-distributed parameters on/off
            * silent: (bool) Console output control
            * defaultDict: (dict[str,str] provide a custom dictionary of default values. If none is provided, defaultConfigValues is used.)
            * simDefParseStack: set(str) list of sim definition files in the current parse stack. Will throw an error if any of these files need to be loaded to generate the current sim definition
                # !include and !create [] from [] statements must form an acyclic graph of files to load (no circular loads)
        
        Example:
            The file contents:  
                'SimControl{  
                    &nbsp;&nbsp;&nbsp;&nbsp;timeDiscretization RK4;  
                }'  
            Would be parsed into a single-key Python dictionary, stored in self.dict:  
            `{ "SimControl.timeDiscretization": "RK4"}`
        
        '''
        self.silent = silent
        ''' Boolean, controls console output '''

        self.fileName = fileName

        self.disableDistributionSampling = disableDistributionSampling
        ''' Boolean - controls whether parameters which have standard deviations specified are actually sampled from a normal distribution. If True, the mean value is always returned. Chief use case for disabling sampling: Checking simulation convergence as the time step / target error is decreased. '''

        self.defaultDict = defaultConfigValues if (defaultDict == None) else defaultDict
        ''' Holds all of the defined default values. These will fill in for missing values in self.dict. Unless a different dictionary is specified, will hold a reference to `defaultConfigValues` '''
        
        self.monteCarloLogger = None 
        ''' Filled in by  Main.runMonteCarloSimulation() if running  Monte Carlo simulation. Type: `MAPLEAF.IO.Logging.MonteCarloLogger` '''

        self.dict = None # type: Dict[str:str]
        ''' Main dictionary of values, usually populated from a simulation definition file '''

        self.simDefParseStack = { self.fileName } if (simDefParseStack == None) else simDefParseStack
        ''' Keeps track of which files have already been loaded in the current parse stack. If these are loaded again we're in a parsing loop '''

        # Parse/Assign main values dictionary
        if dictionary != None:
            self.dict = dictionary
        elif fileName != None:
            self.dict = self._parseSimDefinitionFile(fileName)
        else:
            raise ValueError("No fileName or dictionary provided to initialize the SimDefinition")

        # Initialize tracking of default values used and unaccessed keys
        self._resetUsageTrackers()

        # Check if any probabilistic keys exist
        containsProbabilisticValues = False
        for key in self.dict:
            if "_stdDev" == key[-7:]:
                containsProbabilisticValues = True

        # Initialize instance of random.Random for Monte Carlo sampling
        if not disableDistributionSampling:
            try:
                randomSeed = self.getValue("MonteCarlo.randomSeed")
            except KeyError:
                randomSeed = random.randrange(1000000)
            
            if not silent and containsProbabilisticValues:
                print("Monte Carlo random seed: {}".format(randomSeed))
                
            self.rng = random.Random(randomSeed)
            ''' Instace of random.Random owned by this instance of SimDefinition. Random seed can be specified by the MonteCarlo.randomSeed parameter. Used for sampling all normal distributions for parameters that have std dev specified. '''

            self.resampleProbabilisticValues()            

    def _loadSubSimDefinition(self, path: str):
        ''' 
            In the parsing process, may need to load other sim definition files, use this function when doing that to detect circular references 
            path can be relative to the location of the current file, absolute, or relative to the MAPLEAF install directory
            
            Throws ValueError if circular parsing detected.
            Returns a new SimDefinition object
        '''
        filePath = getAbsoluteFilePath(path, str( Path(self.fileName).parent ))

        if filePath not in self.simDefParseStack:
            self.simDefParseStack.add(filePath)
            subSimDef = SimDefinition(filePath, simDefParseStack=self.simDefParseStack)
            self.simDefParseStack.remove(filePath)
            return subSimDef
        
        else:
            raise ValueError("Encountered circular reference while trying to parse SimDefinition file: {}, which references: {}, which is already in the current parse stack: {}".format(self.fileName, filePath, self.simDefParseStack))

    def _parseDictionaryContents(self, Dict, workingText, startLine: int, currDictName: str, allowKeyOverwriting=False) -> int:
        ''' 
            Parses an individual subdictionary in a simdefinition file.
            Calls itself recursively to parse further sub dictionaries.
            Saves parsed key-value pairs to Dict

            workingText should be of type list[str]

            Returns index of next line to parse
        '''
        i = startLine

        while i < len(workingText):
            line = workingText[i].strip()
            splitLine = line.split()
            
            if splitLine[0] == "!create":
                # Parse derived subdictionary
                i = self._parseDerivedDictionary(Dict, workingText, i, currDictName)

            elif splitLine[0] == "!include":
                # Include contents of another sim definition file
                filePath = line[line.index(" "):].strip() # Handle file names with spaces
                subDef = self._loadSubSimDefinition(filePath)

                # Add keys to current sim definition, inside current dictionary
                for subDefkey in subDef.dict:
                    if currDictName == "":
                        key = subDefkey
                    else:
                        key = currDictName + "." + subDefkey

                    Dict[key] = subDef.dict[subDefkey]

            elif line[-1] == '{':
                # Parse regular Subdictionary
                subDictName = line[:-1] # Remove whitespace and dict start bracket
                
                # Recursive call to parse subdictionary
                if currDictName == "":
                    i = self._parseDictionaryContents(Dict, workingText, i+1, subDictName, allowKeyOverwriting)
                else:
                    i = self._parseDictionaryContents(Dict, workingText, i+1, currDictName + "." + subDictName, allowKeyOverwriting)

            elif line == '}':
                #End current dictionary - continue parsing at next line
                return i
                        
            elif len(splitLine) > 1:
                # Save a space-separated key-value pair
                key = splitLine[0]
                value = " ".join(splitLine[1:])
                if currDictName == "":
                    keyString = key
                else:
                    keyString = currDictName + "." + key

                if not keyString in Dict or allowKeyOverwriting:
                    Dict[keyString] = value
                else:
                    raise ValueError("Duplicate Key: " + keyString + " in File: " + self.fileName)
            
            else:
                # Error: Line not recognized as a dict start/end or a key/value pair
                print(simDefinitionHelpMessage)
                raise ValueError("Problem parsing line {}: {}".format(i, line))

            # Next line
            i += 1

    def _parseDerivedDictionary(self, Dict, workingText, initializationLine: int, currDictName: str) -> int:
        '''
            Parse a 'derived' subdictionary, defined with the !create command in .mapleaf files

            Inputs:
                workingText: (list[str]) lines of text in .mapleaf file
                initializationLine: (int) index of line defining the derived dictionary to be parsed in workingText
                currDictName: (str) name of the dictionary containing the derived dictionary to be parsed. "" if at root level

            Returns:
                (int): index of the last line in the derived subdictionary
        '''
        # workingText[initializationLine] should be something like:
            # '    !create SubDictionary2 from Dictionary1.SubDictionary1{'
        definitionLine = shlex.split(workingText[initializationLine])

        # Figure out complete name of new dictionary
        if currDictName == '':
            derivedDictName = definitionLine[1]
        else:
            derivedDictName = currDictName + '.' + definitionLine[1]

        # Parent dict is last command. Remove opening curly bracket (last character), if present
        dictPath = definitionLine[-1][:-1] if ('{' == definitionLine[-1][-1]) else definitionLine[-1]

        #### Load Parent/Source (Sub)Dictionary ####
        if ":" in dictPath:
            # Importing dictionary from another file
            fileName = dictPath.split(":")[0]              
            subSimDef = self._loadSubSimDefinition(fileName)
            sourceDict = subSimDef.dict
            
            dictPath = dictPath.split(":")[1]
            keysInParentDict = subSimDef.getSubKeys(dictPath)                
        
        else:
            # Deriving from dictionary in current file
            # Get keys from parent dict
            keysInParentDict = self.getSubKeys(dictPath, Dict)
            sourceDict = Dict
        
        if len(keysInParentDict) == 0:
            raise ValueError("ERROR: Dictionary to derive from: {} is not defined before {} in {}.".format(dictPath, derivedDictName, self.fileName))
        
        # Fill out temporary dict, after applying all modifiers, add values to main Dict
        derivedDict = {}

        # Rename all the keys in the parentDict -> relocate them to the new (sub)dictionary
        for parentKey in keysInParentDict:
            key = parentKey.replace(dictPath, derivedDictName)
            derivedDict[key] = sourceDict[parentKey]


        #### Apply additional commands ####
        i = initializationLine + 1
        while i < len(workingText):
            line = workingText[i]
            command = shlex.split(line)

            def removeQuotes(string):
                string = string.replace("'", "")
                return string.replace('"', "")

            if command[0] == "!replace":
                # Get string to replace and its replacement
                toReplace = removeQuotes(command[1])
                replaceWith = removeQuotes(command[-1])

                derivedDictAfterReplace = {}
                for key in derivedDict:
                    newKey = key.replace(toReplace, replaceWith)
                    # .pop() gets the old value and also deletes it from the dictionary
                    newValue = derivedDict[key].replace(toReplace, replaceWith)
                    derivedDictAfterReplace[newKey] = newValue

                derivedDict = derivedDictAfterReplace

            elif command[0] == "!removeKeysContaining":
                stringToDelete = command[1]

                # Search for and remove any keys that contain stringToDelete
                keysToDelete = []
                for key in derivedDict:
                    if stringToDelete in key:
                        keysToDelete.append(key)

                for key in keysToDelete:
                    del derivedDict[key]                

            elif line[0] != "!":
                break # Done special commands - let the regular parser handle the rest

            else:
                raise ValueError("Command: {} not implemented. Try using !replace or !removeKeysContaining".format(line.split()[0]))

            i += 1

        #### Add derivedDict values to Dict ####
        for key in derivedDict:
            # Make sure we don't clobber existing values with poorly thought-out replace commands
            if key not in Dict:
                Dict[key] = derivedDict[key]
            else:
                raise ValueError("Derived dict key {} already exists".format(key, self.fileName))

        #### Parse any regular values in derived dict ####
        return self._parseDictionaryContents(Dict, workingText, i, derivedDictName, allowKeyOverwriting=True)

    def _replaceRelativeFilePathsWithAbsolutePaths(self, Dict):
        ''' 
            Tries to detect paths relative to the MAPLEAF installation directory and replaces them with absolute paths.
            This allows MAPLEAF to work when installed from pip and being run outside its installation directory.
        '''
        if self.fileName != None:
            fileDirectory = os.path.dirname(os.path.realpath(self.fileName))
        else:
            fileDirectory = None

        for key in Dict:
            # Iterate over all keys, looking for file path relative to the MAPLEAF repo
            val = Dict[key]
            
            # Remove leading dot/slash
            if val[:2] == "./":
                val = val[2:]

            if pathIsRelativeToRepository(val):
                # Replace the relative path with an absolute one
                Dict[key] = getAbsoluteFilePath(val)
            
            if isFileName(val):
                # Check if the file path is relative to the location of the simulation definition file
                if fileDirectory != None:
                    possibleLocation = os.path.join(fileDirectory, val)
                    if os.path.exists(possibleLocation):
                        Dict[key] = possibleLocation

    def _parseSimDefinitionFile(self, fileName):
        Dict = {}
        
        # Read all of the file's contents
        file = open(fileName, "r+")
        workingText = file.read()
        file.close()
        
        # Remove comments
        comment = re.compile("(?<!\\\)#.*") 
        workingText = re.sub(comment, "", workingText) 
        
        # Remove comment escape characters
        workingText = re.sub(r"\\(?=#)", "", workingText) 
        
        # Remove blank lines
        workingText = [line for line in workingText.split('\n') if line.strip() != '']
        
        # Start recursive parse by asking to parse the root-level dictionary
        self._parseDictionaryContents(Dict, workingText, 0, "")

        # Look for file paths relative to the MAPLEAF install location, replace them with absolute paths
        self._replaceRelativeFilePathsWithAbsolutePaths(Dict)

        return Dict

    #### Normal Usage ####
    def resampleProbabilisticValues(self, Dict=None):
        '''
            Normal Distribution Sampling:
                If (key + "_stdDev") exists and the value being returned is a scalar or Vector value, returns a scalar or vector sampled from a normal distribution
                    Where the mean of the normal distribution is taken to be the (original) value of 'key' (moved to 'key_mean' when this function first runs) and the standard deviation of the distribution is the value of 'key_stdDev'
                    For a vector value, a vector of standard deviations is expected
                For repeatable sampling, set the value "MonteCarlo.randomSeed" in the file loaded by this class
        '''
        if Dict is None:
            Dict = self.dict

        if not self.disableDistributionSampling:
            keys = list(Dict.keys()) # Get a list of keys at the beginning to avoid issues from the number of keys changing during iterations
            
            for key in keys:
                ### Sample any probabilistic values from normal distribution ###
                stdDevKey = key + "_stdDev"
                
                if stdDevKey in Dict:
                    logLine = None
                    meanKey = key + "_mean"

                    try:
                        meanString = Dict[meanKey]
                    except KeyError:
                        # Take the value of the variable as the mean if a _mean value is not provided
                        meanString = Dict[key]
                        Dict[meanKey] =  meanString

                    # Try parsing scalar values
                    try:
                        mu = float(meanString)
                        sigma = float(Dict[stdDevKey])

                        sampledValue = self.rng.gauss(mu, sigma)
                        Dict[key] = str(sampledValue)

                        logLine = "Sampling scalar parameter: {}, value: {:1.3f}".format(key, sampledValue)

                    except ValueError:
                        # Try parsing vector value
                        try:
                            muVec = Vector(meanString)
                            sigmaVec = Vector(Dict[stdDevKey])

                            sampledVec = Vector(*[ self.rng.gauss(mu, sigma) for mu, sigma in zip(muVec, sigmaVec)])
                            Dict[key] =  str(sampledVec)

                            logLine = "Sampling vector parameter: {}, value: ({:1.3f})".format(key, sampledVec)
                            
                        except ValueError:
                            # ValueError throws if either conversion to Vector fails
                            # Note that monte carlo / probabilistic variables can only be scalars or vectors
                            print("ERROR: Unable to parse probabilistic value: {} for key {} (or {} for key {}). Note that probabilistic values must be either scalars or vectors of length 3.".format(meanString, meanKey, self.getValue(stdDevKey), stdDevKey))
                            raise
                    
                    ### Logging ###
                    if logLine != None:
                        if self.monteCarloLogger != None:
                            self.monteCarloLogger.log(logLine)
                        elif not self.silent:
                            print(logLine)

    def getValue(self, key: str) -> str:
        """
            Input:
                Key should be a string of format "DictionaryName.SubdictionaryName.Key"
            Output:
                Always returns a string value
                Returns value from defaultConfigValues if key not present in current SimDefinition's dictionary
        """
        # Remove any whitespace from the key
        key = key.strip()

        ### Find string/mean value ###
        if self.dict.__contains__(key):
            if key in self.unaccessedFields: # Track which keys are accessed
                self.unaccessedFields.remove(key)
            return self.dict[key]
        
        elif key in self.defaultDict:
            self.defaultValuesUsed.add(key)
            return self.defaultDict[key]
        else:
            # Check if there's a class-based default value to return
            classBasedDefaultValue = self._getClassBasedDefaultValue(key)
            
            if classBasedDefaultValue != None:
                return classBasedDefaultValue
            else:
                raise KeyError("Key: " + key + " not found in {} or default config values".format(self.fileName))

    def setValue(self, key: str, value) -> None:
        '''
            Will add the entry if it's not present
        '''
        # The .strip() removes whitespace
        self.dict[key.strip()] = value

    def removeKey(self, key: str):
        if key in self.dict:
            return self.dict.pop(key)
        else:
            print("Warning: " + key + " not found, can't delete")
            return None

    def setIfAbsent(self, key: str, value):
        ''' Sets a value, only if it doesn't currently exist in the dictionary '''
        if not key in self.dict:
            self.setValue(key, value)

    def writeToFile(self, fileName: str, writeHeader=True) -> None:
        ''' 
            Write a (potentially modified) sim definition to file.
            Newly written file will not contain any comments! 
        '''
        self.fileName = fileName

        with open(fileName, 'w') as file:
            # Extract the fileName from the fileName variable, which may contain other folder names
            dictName = re.sub("^.*/", "", fileName)

            # Write Header
            if writeHeader:
                file.write("# MAPLEAF\n")
                file.write("# File: {}\n".format(fileName))
                file.write("# Autowritten on: " + str(datetime.now()) + "\n")

            # Sorting the keys before iterating through them ensures that dictionaries will be stored together
            sortedDict = sorted(self.dict.items())
            currDicts = []
            for key in sortedDict:
                key = key[0]
                dicts = key.split('.')[:-1]

                # Need to get be in the appropriate dictionary before writing the key, value pair
                if dicts != currDicts:
                    
                    #Close any uneeded dictionaries
                    dictDepth = currDicts.__len__()
                    while dictDepth > 0:
                        if dictDepth > dicts.__len__():
                            file.write("\t"*(dictDepth-1) + "}\n")
                        elif currDicts[dictDepth-1] != dicts[dictDepth-1]:
                            file.write("\t"*(dictDepth-1) + "}\n")
                        else:
                            break
                        
                        dictDepth = dictDepth - 1

                    openedNewDict = False

                    #Open any new dictionaries
                    while dictDepth < dicts.__len__():
                        newDict = dicts[dictDepth]
                        file.write("\n" + "\t" * dictDepth + newDict + "{\n")
                        dictDepth = dictDepth + 1
                        openedNewDict = True
                    
                    if not openedNewDict:
                        # If no new dictionary was openend after closing unneeded ones, add a spacing line before writing keys/values
                        file.write("\n")

                    currDicts = dicts

                #Add the key, value
                dictDepth = currDicts.__len__()
                realKey = re.sub("^([^\.]*\.)+", "", key)
                file.write( "\t"*dictDepth + realKey + "\t" + self.dict[key] + "\n")

            #Close any open dictionaries
            dictDepth = currDicts.__len__()
            while dictDepth > 0:
                dictDepth = dictDepth - 1
                file.write("\t"*dictDepth + "}\n")

    #### Introspection / Key Gymnastics ####
    def findKeysContaining(self, keyContains: List[str]) -> List[str]:
        '''
            Returns a list of all keys that contain any of the strings in keyContains
            
            ## Example  
                findKeysContaining(["class"]) ->  
                [ "Rocket.class", "Rocket.Sustainer.class", "Rocket.Sustainer.Nosecone.class", etc... ]
        '''
        if not isinstance(keyContains, list):
            keyContains = [ keyContains ]
        
        matchingKeys = []
        for key in self.dict.keys():
            match = True
            for str in keyContains:
                if str not in key:
                    match = False
                    break
            
            if match:
                matchingKeys.append(key)
        
        if len(matchingKeys) > 0:
            return matchingKeys
        else:
            return None

    def getSubKeys(self, key: str, Dict=None) -> List[str]:
        '''
            Returns a list of all keys that are children of key

            ## Example  
                getSubKeys("Rocket") ->  
                [ "Rocket.position", "Rocket.Sustainer.NoseCone.mass", "Rocket.Sustainer.RecoverySystem.position", etc... ]
        '''
        #TODO: Improve speed by keeping dict sorted, then use binary search to locate first/last subkeys
        Dict = self.dict if (Dict == None) else Dict

        subKeys = []
        for currentKey in Dict.keys():
            if isSubKey(key, currentKey):
                subKeys.append(currentKey)
        
        return subKeys

    def getImmediateSubKeys(self, key: str) -> List[str]:
        """ 
            Returns all keys that are immediate children of the parentKey (one 'level' lower)
            
            .. note:: Will not return subdictionaries, only keys that have a value associated with them. Use self.getImmediateSubDicts() to discover sub-dictionaries

            ## Example:
                getImmediateSubKeys("Rocket") ->  
                [ "Rocket.name", "Rocket.position", "Rocket.velocity", etc...]
        """
        results = set()
        for potentialChildKey in self.dict.keys():
            # Iterate through all keys - check if they are children of currentPath
            if isSubKey(key, potentialChildKey):
                # If so, get the part of the key that is the immediate child of currentPath
                immediateSubkey = getImmediateSubKey(key, potentialChildKey)
                
                if immediateSubkey in self.dict:
                    # If we haven't got it already, save it
                    results.add(immediateSubkey)

        return list(results)

    def getImmediateSubDicts(self, key: str) -> List[str]:
        '''
            Returns list of names of immediate subdictionaries

            ## Example
                getImmediateSubDicts("Rocket") ->
                [ "Rocket.StageOne", "Rocket.StageTwo", "Rocket.ControlSystem", etc... ]

            .. note:: This example would not return a dictionry like: "Rocket.StageOne.FinSet" because it's not an immediate subdictionary of "Rocket"
        '''
        keyLevel = getKeyLevel(key)
        subKeys = self.getSubKeys(key)

        subDictionaries = set()
        for subKey in subKeys:
            subKeyLevel = getKeyLevel(subKey)
            if subKeyLevel - keyLevel > 1:
                # A subkey would have 1 level higher
                # A subkey of a subdictionary would have 2 levels higher - this is what we're looking for
                subDictKey = getParentKeyAtLevel(subKey, keyLevel+1)
                subDictionaries.add(subDictKey)
        
        return list(subDictionaries)

    def _getClassBasedDefaultValue(self, key: str) -> Union[str, None]:
        ''' 
            Returns class-based default value from defaultConfigValues if it exists. Otherwise returns None 
            
            Will attempt to find class-based default values for every longer prefixes of a key:
                key = "Rocket.Sustainer.canards.trailingEdge.shape"
                Attempt1 = "Rocket.Sustainer.canards.trailingEdge.class" -> Fail
                Attempt2 = "Rocket.Sustainer.canards.class" -> FinSet -> look up 'FinSet.trailingEdge.shape' in defaultDict -> if there, return it, otherwise return None
        '''
        splitLevel = getKeyLevel(key)

        while splitLevel >= 0:
            prefix, suffix = splitKeyAtLevel(key, splitLevel)
            
            try:
                classKey = prefix + ".class"
                className = self.dict[classKey]                

                # As soon as we arrive at an item with a class, search terminates
                try:
                    classBasedDefaultKey = className + "." + suffix
                    defaultValue = self.defaultDict[classBasedDefaultKey]

                    # Track that we've used a default value
                    self.defaultValuesUsed.add(classBasedDefaultKey)
                    
                    # if the classKey was useful, count it as 'used'
                    if classKey in self.unaccessedFields: 
                        self.unaccessedFields.remove(classKey)
                        
                    return defaultValue
                except KeyError:
                    return None # class-based default value not found
            
            except KeyError:
                pass # prefix.class not present

            # Move one level up the dictionary for next attempt
            splitLevel -= 1
        
        return None

    #### Usage Reporting ####
    def printUnusedKeys(self):
        '''
            Checks which keys in the present simulation definition have not yet been accessed.
            Prints a list of those to the console.
        '''
        if len(self.unaccessedFields) > 0:
            print("\nWarning: The following keys were loaded from: {} but never accessed:".format(self.fileName))
            for key in sorted(self.unaccessedFields):
                value = self.dict[key]
                print("{:<45}{}".format(key+":", value))
            print("")

    def printDefaultValuesUsed(self):
        '''
            Checks which default values have been used since the creation of the current instance of SimDefinition. Prints those to the console.
        '''
        if len(self.defaultValuesUsed):
            print("\nWarning: The following default values were used in this simulation:")
            for key in sorted(self.defaultValuesUsed):
                value = self.defaultDict[key]
                print("{:<45}{}".format(key+":", value))
            print("\nIf this was not intended, override the default values by adding the above information to your simulation definition file.\n")
        
    def _resetUsageTrackers(self):
        # Create a dictionary to keep track of which attributed have been accessed (initially none)
        self.unaccessedFields = set(self.dict.keys())
        # Create a list to track which default values have been used
        self.defaultValuesUsed = set()

    #### Utilities ####
    def __str__(self):
        result = ""
        result += "File: " + self.fileName + "\n"

        for key, value in self.dict.items():
            result += "{}: {}\n".format(key, value)

        result += "\n"

        return result

    def __eq__ (self, simDef2):
        try:
            if self.dict == simDef2.dict:
                return True
            else:
                return False
        except AttributeError:
            return False

    def __contains__(self, key):
        ''' Only checks whether 'key' was parsed from the file. Ignores default values '''
        return key in self.dict

################### Functions for dealing with string keys ########################
def isSubKey(potentialParent:str, potentialChild:str) -> bool:
    """
        ## Example 
        `isSubKey("Rocket", "Rocket.name")` -> True
        `isSubKey("SimControl", "Rocket.name")` -> False
    """
    if potentialParent == "":
        # All keys are children of an empty key
        return True
    
    pLength = len(potentialParent)
    cLength = len(potentialChild)

    if cLength <= pLength:
        # Child key can't be shorter than parent key
        return False
    elif potentialChild[:pLength] == potentialParent and potentialChild[pLength] == ".":
        # Child key must contain parent key
        return True
    else:
        return False

def getKeyLevel(key:str) -> int:
    """
        Sums the number of dots in the key 
        ## Example 
            getKeyLevel("Rocket") -> 0  
            getKeyLevel("Rocket.name") -> 1
    """
    if len(key) == 0:
        return -1
    else:
        return len(key.split('.'))-1

def getParentKeyAtLevel(key:str, desiredLevel:int) -> str:
    """
        >>> getParentKeyAtLevel('Rocket.Sustainer.Nosecone.mass', 0)
        'Rocket'
        >>> getParentKeyAtLevel('Rocket.Sustainer.Nosecone.mass', 1)
        'Rocket.Sustainer'
        >>> getParentKeyAtLevel('Rocket.Sustainer.Nosecone.mass', 2)
        'Rocket.Sustainer.Nosecone'
    """
    desiredParts = key.split('.')[0:desiredLevel+1]
    return '.'.join(desiredParts)

def getImmediateSubKey(parent, child):
    """ 
        Takes the parent key, adds one level of the child key:  

        ## Example
        >>> getImmediateSubKey('Rocket', 'Rocket.Sustainer.name')
        'Rocket.Sustainer'
    """
    if not isSubKey(parent, child):
        raise ValueError("{} is not a subkey of {}".format(child, parent))

    parentKeyPlusOneLevel, _ = splitKeyAtLevel(child, getKeyLevel(parent)+1)
    return parentKeyPlusOneLevel

def splitKeyAtLevel(key:str, prefixLevel:int) -> Tuple[str]:
    ''' 
        0 <= level <= getKeyLevel(key)
        ### Example
        >>> splitKeyAtLevel("Rocket", 0)
        ('Rocket', '')
        >>> splitKeyAtLevel("Rocket.Sustainer", 0)
        ('Rocket', 'Sustainer')
        >>> splitKeyAtLevel("Rocket.Sustainer.position", 1)
        ('Rocket.Sustainer', 'position')
    '''
    n = prefixLevel + 1
    keyNames = key.split('.')
    prefix = ".".join(keyNames[:n])
    suffix = ".".join(keyNames[n:])
    return prefix, suffix

def isFileName(value:str) -> bool:
    expectedExtensions = [".csv", '.pdf', '.mapleaf', '.txt', '.py', '.eng'] # And file extensions here to have filled paths in simulation definition files ending in these extensions auto corrected
    for ext in expectedExtensions:
        if ext in value:
            return True
    
    return False

def pathIsRelativeToRepository(possiblePath:str) -> bool:
    return  len(possiblePath) > 8 and possiblePath[:8] == "MAPLEAF/"

def getAbsoluteFilePath(relativePath: str, alternateRelativeLocation: str = "", silent=False) -> str:
    ''' 
        Takes a path defined relative to the MAPLEAF repository and tries to return an absolute path for the current installation.
        alternateRelativeLocation (str) location of an alternate file/folder the path could be relative to
        Returns original relativePath if an absolute path is not found
    '''
    # Check if path is relative to MAPLEAF installation location
    # This file is at MAPLEAF/IO/SimDefinition, so MAPLEAF's install directory is three levels up
    pathToMAPLEAFInstallation = Path(__file__).parent.parent.parent

    relativePath = Path(relativePath)
    absolutePath = pathToMAPLEAFInstallation / relativePath

    if absolutePath.exists():
        return str(absolutePath)
    else:
        if alternateRelativeLocation != "":
            # Try alternate location
            alternateLocation = Path(alternateRelativeLocation)
            
            if alternateLocation.is_file():
                # If the alternate location provided is a file path, check if the file is in the parent directory
                absolutePath = alternateLocation.parent / relativePath
            else:
                absolutePath = alternateLocation / relativePath

            if absolutePath.exists():
                return str(absolutePath)
                
    if not silent:
        if ".pdf" not in str(relativePath): # Assume .pdf files are outputs, may not be created yet - so we wouldn't expect to find them immediately!
            print("WARNING: Unable to compute absolute path replacement for: {}, try providing an absolute path".format(relativePath))
        
    return str(relativePath)
