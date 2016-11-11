import arcpy, os, sys               # General Imports
import gc; gc.disable()             # Don't allow garbage collection

# Change after the insallation of the ArcToolBox
pythonScriptPath = "C://Users/eggimasv/URBANDENSITY/P4/"

def rewritePath(inPath):
    ''' Replace Characters in string path to get correct path.'''
    replaceList = [["\a","REPLACEA"], ["\t", "REPLACET"], ["\r","REPLACER" ], ["\f", "REPLACEF"], ["\b", "REPLACEB"], ["\n", "REPLACEN"], ["\\", "//"], ["REPLACEA", "/a"], ["REPLACET","/t" ], ["REPLACER", "/r"], ["REPLACEF", "/f"], ["REPLACEB", "/b"], ["REPLACEN", "/n"]]
    for c in replaceList:
        inPath = inPath.replace(c[0], c[1])
    return inPath

# Paths
pythonPath = os.getcwd()
sys.path.append(pythonPath)
sys.path.append(pythonScriptPath)                           # Path where python scripts are stored

# SNIP Imports    
from SNIP_functions import *                                # Import Functions
from SNIP_costs import *                                    # Import cost functions

toolboxes = ["Data Management Tools.tbx"]
arcpy.env.overwriteOutput = True

# ArcGIS System Arguments
txtFileInputPath = "C://_SCRAP_FOLDERSTRUCTURE//430900//"# 414100

in_street = txtFileInputPath + "streetRailMerge.shp"
buildings = txtFileInputPath + "USU_USUandSingleBuildings.shp"
inDHM = txtFileInputPath + "dem_point.shp"
outListFolder = txtFileInputPath #+ "_RESULTS"
demAlreadyReadOut = 0                                   # 1: Dem is already read out 0: Read out DEM

#os.mkdir(outListFolder)                         # Create Main Folder

# Model parameters (based parameters as in Eggimann et al. 2015)
# ========================================================================
  
# Sewer related
maxTD = 8                                   # [m] Maximum trench depth
minTD = 0.25                                # [m] Min trench depth
minSlope = 1                                # [%] Criteria of minimum slope without pumps needed
stricklerC = 85                             # [m^1/3 s^-1] Stricker Coefficient
EW_Q = 0.162                                # [m3 / day] 1 EW is equal to 162 liter. This factor must be the same as for the GIS-Files
    
# Cost related
resonableCostsPerEW = 7540                  # [currency] Reasonable Costs
pricekWh = 0.20                             # [currency / kWh] price per kWh of electricity 
pumpingYears = 30                           # [years] Pump lifespan
discountYearsSewers = 80                    # [years] Pipe lifespan
wwtpLifespan = 33                           # [years] WWTP lifespan
interestRate = 2                            # [%] Real interest rate
operationCosts = 5                          # [currency / meter] operation costs per meter pipe per year
pumpInvestmentCosts = 500                   # [currency] Fix costs of pumps
fc_SewerCost = 0                            # [-20% - 20%] Used for Sensitivity Analysis to shift cost curve  (e.g. 10 % = 0.1)
fc_wwtpOpex = 0                             # [-20% - 20%] Used for Sensitivity Analysis to shift cost curve  (e.g. 10 % = 0.1)
fc_wwtpCapex = 0                            # [-20% - 20%] Used for Sensitivity Analysis to shift cost curve 
        
# Algorithm related
f_street = 1.7                              # [-] Factor to set How close the sewer follow the road network
f_merge = 1.4                               # [-] Factor do determine how the WWTPS are merged.
f_topo = 1.2                                # [-] Factor weighting the dem graph creation for the a* algorithm
    
neighborhood = 100                          # [m] Defines how large the neighbourhood for the a-Star Algorithm (Needs to be at least twice the raster size)     
AggregateKritStreet = 100                   # [m] How long the distances on the roads can be in maximum be before they get aggregated on the street network (must not be 0)
border = 3000                               # [m] How large the virtual dem borders are around topleft and bottom
tileSize = 50                               # [m] for selection of density based starting node
    
pipeDiameterPrivateSewer = 0.25             # Cost Assumptions private sewers: Pipe Diameter
avgTDprivateSewer = 0.25                    # Cost Assumptions private sewers: AVerage Trench Depth
    
# ArcGIS Representation related
drawHouseConnections = 1                    # 1: House connections are drawn in ArcGIS, 0: House Connections are not drawn in ArcGIS
interestRate = float(interestRate) / 100.0  # Reformulate real interest rate

# Add parameters into List for SNIP Algorithm
InputParameter = [minTD, maxTD, minSlope, f_merge, resonableCostsPerEW, neighborhood, f_street, pricekWh, pumpingYears, discountYearsSewers, interestRate, stricklerC, EW_Q,  wwtpLifespan, operationCosts, pumpInvestmentCosts,  f_topo, fc_SewerCost, fc_wwtpOpex, fc_wwtpCapex]

outListStep_point = outListFolder + "aggregated_nodes.shp"
outPathPipes = outListFolder + "sewers.shp"
outList_nodes = outListFolder + "nodes.shp"
outList_pumpes = outListFolder + "pumpes.shp"
outList_WWTPs = outListFolder + "WWTPs.shp"
aggregatetStreetFile = outListFolder  + "streetGraph.shp"
allNodesPath = outListFolder + "allNodes.shp"
outPath_StartNode = outListFolder + "startnode.shp"

# Create .txt files for SNIP Calculation and data preparation
buildPoints = readBuildingPoints(buildings)                                                                 # Read out buildings. read ID from Field

anzNumberOfConnections = len(buildPoints)                                                                   # used for setting new IDs
rasterPoints, rasterSize = readRasterPoints(inDHM, anzNumberOfConnections)                                  # Read out DEM
rasterSizeList = [rasterSize]                                                                               # Store raster size

nearPoints = readClosestPointsAggregate(buildings)                                                          # Read the near_X, near_Y -points of the buildings into a list 
aggregatetPoints, buildings = aggregate(nearPoints, AggregateKritStreet, outListStep_point, minTD)          # Aggregate houses on the street and create point file (sewer inlets).
updateFieldStreetInlets(outListStep_point)                                                                  # Update field for the sewer inlets
writefieldsStreetInlets(outListStep_point, aggregatetPoints)                                                # Write to shapefile
splitStreetwithInlets(in_street, outListStep_point, aggregatetStreetFile)                                   # Split street network with the sewer inlets
updatefieldsPoints(aggregatetStreetFile)                                                                    # Update fields in splitted street and add StreetID, the height to each points is assigned from closest DEM-Point
streetVertices = readOutAllStreetVerticesAfterAggregation(aggregatetStreetFile, rasterPoints, rasterSize)
aggregatetPoints =  correctCoordinatesAfterClip(aggregatetPoints, streetVertices)                           # Because after ArcGIS Clipping slightly different coordinate endings, change them in aggregatetPoints (different near-analysis)
forSNIP, aggregatetPoints = assignStreetVertAggregationMode(aggregatetPoints, streetVertices, minTD)        # Build dictionary with vertexes and save which buildings are connected to which streetInlet   
drawAllNodes(streetVertices, allNodesPath)                                                                  # Write out all relevant nodes
updateFieldNode(allNodesPath)
writefieldsAllNodes(allNodesPath, streetVertices)
edges = createStreetGraph(aggregatetStreetFile)                                                             # Create list with edges from street network
edgeList = addedgesID(edges, streetVertices)                                                                # Assign id and distance to edges
streetGraph = appendStreetIDandCreateGraph(edgeList)                                                        # Create graph
aggregatetPoints = assignHighAggregatedNodes(aggregatetPoints, rasterPoints, rasterSize, minTD)             # Assign High to Aggregated Nodes
forSNIP = addBuildingsFarFromRoadTo(aggregatetPoints, forSNIP)                                              # Add all buildings far from the road network 
_, startnode, startX, startY = densityBasedSelection(aggregatetPoints, tileSize)                            # Select start node with highest density  

writeTotxt(outListFolder, "inputParameters", InputParameter)                                                # Write to .txt files
writeTotxt(outListFolder, "rasterPoints", rasterPoints)                                                     # Write to .txt files
writeTotxt(outListFolder, "rastersize", rasterSizeList)                                                     # Write to .txt files
writeTotxt(outListFolder, "buildPoints", buildPoints)                                                       # Write to .txt files
writeTotxt(outListFolder, "forSNIP", forSNIP)                                                               # Write to .txt files
writeTotxt(outListFolder, "aggregatetPoints", aggregatetPoints)                                             # Write to .txt files
writeTotxt(outListFolder, "forSNIP", forSNIP)                                                               # Write to .txt files
writeTotxt(outListFolder, "streetVertices", streetVertices)                                                 # Write to .txt files
writeTotxt(outListFolder, "edgeList", edgeList)                                                             # Write to .txt files
writeToDoc(outListFolder, "streetGraph", streetGraph)                                                       # Write to .txt files
writeTotxt(outListFolder, "buildings", buildings)                                                           # Write to .txt files

arcpy.AddMessage("...ready for SNIP Calculation")