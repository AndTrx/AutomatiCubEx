AutomatiCubEx.py - GUI guide and standard CubEx workflow
=========================================================

Overview
--------
AutomatiCubEx.py is a graphical interface designed to guide the analysis of astronomical FITS datacubes and FITS images using CubEx and the CubEx Tools. The main goal is to make the extraction of extended emission around a source easier, interactive, and reproducible.

The interface allows the user to:

- load a FITS datacube or a 2D FITS image;
- inspect individual spectral slices of a cube;
- inspect a wavelength or spectral-pixel axis when available from the FITS header;
- select a source position directly on the image;
- extract and display a spectrum from a selected pixel or from a circular aperture;
- select a spectral region directly on the spectrum;
- create images from slices, spectral regions, or CubEx masks;
- run CubEx tools from the GUI;
- save outputs in the same directory as the input data;
- store the parameters used for each action in a CSV registry table;
- manually select input/output files for parameters that require paths;
- interactively adjust image cuts in a DS9/QFitsView-like way;
- manually set image cuts, including negative values;
- visualize the colorbar of the currently displayed image.

The intended use case is the analysis of faint extended emission around bright sources, for example quasars or galaxies, where one typically needs to subtract the PSF, subtract the continuum/background, isolate a spectral region, detect extended emission with CubEx, and generate moment maps.


1. Graphical interface functionality
====================================

1.1 Loading FITS files
----------------------
Use the Project / Files panel to load data.

Main buttons:

- Load FITS cube:
  Opens a FITS file. The file may be a 3D datacube or a 2D image.

- Open another FITS:
  Adds another FITS file to the internal list of loaded files.

- Reload current:
  Reloads the currently selected file from disk. This is useful after overwriting a FITS file with an action such as Binarize3DMask.

- Loaded file:
  Drop-down menu listing the files opened in the current session. Use it to switch between input cubes, processed cubes, masks, and images.

If the loaded file is a 3D cube, the GUI displays an image slice and a spectrum. If the loaded file is a 2D image, only the image panel is meaningful and the spectrum panel remains empty.


1.2 Setting the CubEx path
--------------------------
Use Set CubEx path to select the root directory of the CubEx installation. This should be the directory that contains the CubEx executable and the Tools/ directory.

Expected structure:

CubEx-master/
    CubEx
    Tools/
        Cube2Im
        Cube2Spc
        CubeBKGSub
        CubePSFSub
        CubeSel
        CubeReplace
        ...

Most CubEx tools are called from CubEx-master/Tools/, while CubEx itself is called from CubEx-master/CubEx.


1.3 Action registry table
-------------------------
Use Set action table to choose or create a CSV file that stores the parameters used by the GUI actions.

The registry table is useful for reproducibility. For each input cube or image, AutomatiCubEx stores:

- the input filename;
- the last action performed;
- the output file;
- the command preview;
- the parameters used by that action.

If the same cube is processed again, the row corresponding to that cube is updated. If a new cube is processed, a new row is added.


1.4 Image viewer
----------------
The image viewer displays either:

- one spectral slice of a 3D cube;
- the mean image over a selected spectral region;
- the median image over a selected spectral region;
- a loaded 2D FITS image.

The viewer uses a logarithmic display when positive values are available. The maximum value is computed from the displayed image. The cuts can then be changed interactively or manually.

Basic image interactions:

- left click on the image:
  selects the source position and draws a cross at the selected x,y position;

- zoom/pan toolbar:
  standard Matplotlib toolbar for zooming and panning;

- zoom persistence:
  once an image zoom is set, it is preserved when selecting a new pixel, changing the spectral slice, or changing the displayed image mode;

- Cuts ON/OFF:
  enables DS9/QFitsView-like interactive cut adjustment;

- click and drag while Cuts is ON:
  changes the cuts interactively. Horizontal and vertical motion change the image contrast and brightness/cut level;

- Set cuts:
  manually enters vmin and vmax. Negative values are allowed;

- colorbar:
  shows the currently displayed intensity scale and updates when cuts are changed.


1.5 Spectral slice slider
-------------------------
For 3D cubes, the spectral slice slider changes the spectral layer displayed in the image viewer.

The current spectral pixel and wavelength are shown in the right panel when wavelength calibration is available in the FITS header.

The GUI currently estimates the wavelength axis from standard FITS header keywords:

CRVAL3, CDELT3 or CD3_3, CRPIX3.

If these keywords are not available, the x-axis of the spectrum is shown in spectral pixels.


1.6 Spectrum viewer
-------------------
For 3D cubes, the bottom panel shows the spectrum extracted from the selected position.

If no source is selected, the displayed spectrum is the median spectrum of the cube.

If a source is selected with the cross, the displayed spectrum is extracted from:

- the selected pixel, if aperture radius = 0;
- the mean flux inside a circular aperture, if aperture radius > 0.

The aperture radius is set in pixels using the Aperture radius for spectrum field.

The vertical dashed line shows the currently displayed spectral slice.

The spectrum zoom is preserved when changing the selected pixel or scrolling the cube.


1.7 Selecting a spectral region
-------------------------------
A spectral region can be selected directly on the spectrum by click-dragging horizontally.

This region is used by several actions as a default value, for example:

- maskpix for PSF subtraction or background subtraction;
- zmin/zmax for CubeSel;
- displayed mean/median image over the selected spectral interval.

The selected region is shown in the right panel both in spectral pixels and, when available, in wavelength units.


1.8 Image extraction mode
-------------------------
The image extraction mode controls what is shown in the image viewer.

Available modes:

- slice:
  display a single spectral layer;

- mean selected region:
  display the mean flux image over the selected spectral region;

- median selected region:
  display the median flux image over the selected spectral region.

The Apply selected spectral region button updates the displayed image using the selected region.


1.9 File path parameters and Browse buttons
-------------------------------------------
For action parameters that represent file paths, the GUI provides a Browse button.

This is useful for parameters such as:

- input cube;
- output cube;
- idcube;
- mask3d;
- SourceMask;
- LayerMaskList;
- VarFile;
- SBmap;
- KinMap;
- output_mask.

The file dialog opens by default in the directory of the currently loaded FITS file, making it easier to select products produced in the same analysis folder.


2. Standard analysis workflow
=============================

The following workflow is recommended to extract extended emission around a source from a datacube.

The standard sequence is:

1. Cube2Im to generate a white-light image.
2. PSF subtraction without a mask, if needed.
3. PSF subtraction with a spectral mask, if needed.
4. BKG subtraction / continuum subtraction.
5. CubeSel to cut the cube around the emission line.
6. CreateMask to generate a 2D source mask from the white-light image.
7. Inspect the SourceMask and identify the source ID to be unmasked or masked.
8. CubEx to extract a 3D detection mask of the extended emission.
9. Binarize3DMask to keep only the selected 3D object ID and convert it to a binary mask.
10. CreateMaps to generate surface-brightness and kinematic moment maps.

The details of each action are described below.


3. Actions and parameters
=========================

3.1 Cube2Im - create a white-light or narrow-band image
-------------------------------------------------------
Purpose:
Cube2Im converts a datacube into a 2D image. In the standard workflow, it is first used to create a white-light image from the original or processed cube. This image is later used by CreateMask to build a SourceMask.fits file.

Typical use:

Cube2Im -cube input_cube.fits -out input_cube.IM.fits

In the GUI:
Actions -> Cube2Im

Important parameters:

- Input cube:
  The FITS cube used to generate the image.

- Output file:
  The output 2D FITS image. For a white-light image, use a name such as input_cube.IM.fits.

- idcube:
  Optional 3D mask cube. If provided, Cube2Im can extract an image only from voxels belonging to a selected object ID.

- id:
  Object ID to use inside idcube. For binary masks produced by Binarize3DMask, use id = 1.

- idpad:
  Spatial/spectral padding around the selected object ID. Typical values are 5-20. Use a larger value if the mask is too tight.

- nl:
  Number or mode for selecting spectral layers. In many CubEx workflows, nl = -1 means that the spectral region is automatically defined from the object mask.

- nlpad:
  Number of extra spectral layers added around the object. Typical values: 0, 3, 5.

- gsm:
  Gaussian smoothing radius for the output image. Typical values: 0, 1, 2.

- imtype:
  Type of image to produce. Common values:
  flux    : surface-brightness / flux map
  vmap    : velocity / wavelength centroid map

- sbscale:
  If .true., scales the output as surface brightness when appropriate.

- vzero:
  Reference wavelength used for velocity maps.

- writeNaN:
  If .true., writes NaN values outside the selected regions.

Standard first step:

1. Load the original cube.
2. Actions -> Cube2Im.
3. Set output file to input_cube.IM.fits.
4. Leave idcube empty.
5. Apply.
6. Load the resulting 2D image to inspect the field.


3.2 CubePSFSub - PSF subtraction without mask
---------------------------------------------
Purpose:
CubePSFSub subtracts the PSF of a bright unresolved source, for example a quasar, from the datacube.

This step is useful when the bright source dominates the field and may hide faint extended emission.

Typical use without mask:

CubePSFSub -cube input_cube.fits -out input_cube_PSFSub.fits -x Xsrc -y Ysrc -nbins -1 -zPSFsize 150 -rmin 1 -rmax 25 -recenter .true.

In the GUI:
Actions -> CubePSFSub

Recommended procedure:

1. Load the cube.
2. Select the source center by clicking on the image.
3. Open Actions -> CubePSFSub.
4. The x and y parameters should be filled automatically from the selected cross position.
5. Leave maskpix empty for PSF subtraction without mask.
6. Apply and inspect the output cube.

Important parameters:

- x, y:
  Pixel coordinates of the source center. These can be selected interactively by clicking on the image.

- nbins:
  Number of spectral bins used to build the PSF model. A value of -1 usually means that the tool uses its default/internal binning.

- zPSFsize:
  Spectral window size used for PSF construction. Typical value: 150.

- rmin:
  Inner radius excluded from the PSF estimation, in pixels. Typical value: 1.

- rmax:
  Outer radius used to estimate the PSF, in pixels. Typical values: 20-30.

- recenter:
  If .true., recenters the PSF model.

- maskpix:
  Spectral pixel interval to mask during PSF modeling. Leave empty for no mask.

- withvar:
  If .true., propagates or handles variance information when available.

Output:
A PSF-subtracted cube, usually named input_cube_PSFSub.fits.


3.3 CubePSFSub - PSF subtraction with spectral mask
---------------------------------------------------
Purpose:
This mode is used when the source has strong extended emission in a spectral interval that should not be used to build the PSF model.

For example, if Ly-alpha extended emission is expected between spectral pixels 565 and 1113, one can mask this region during the PSF-subtraction step.

Typical use:

CubePSFSub -cube input_cube.fits -out input_cube_PSFSub.fits -x Xsrc -y Ysrc -nbins -1 -zPSFsize 150 -rmin 1 -rmax 25 -maskpix "565 1113"

Recommended procedure:

1. Load the cube.
2. Select the source center on the image.
3. Select the spectral region containing the expected extended emission on the spectrum.
4. Open Actions -> CubePSFSub.
5. The GUI should fill x, y, and maskpix automatically.
6. Apply and inspect the output.

Important additional parameter:

- maskpix:
  Spectral-pixel interval excluded from the PSF modeling. This is usually set from the spectral region selected in the spectrum viewer.

Notes:
The mask should include the wavelength region where extended emission may be present. If this region is not masked, the PSF model may subtract part of the nebular emission.


3.4 CubeBKGSub - background / continuum subtraction
---------------------------------------------------
Purpose:
CubeBKGSub subtracts the continuum/background from the cube using median filtering. This is one of the most important steps before searching for faint extended emission.

Typical use:

CubeBKGSub -cube input_cube.fits -out input_cube_BKGSub.fits -bpsize "1 1 45" -bfrad "0 0 2" -maskpix "565 1113"

In the GUI:
Actions -> CubeBKGSub

Recommended procedure:

1. Load the cube to be continuum-subtracted, usually the PSF-subtracted cube.
2. Select the spectral region containing the emission line.
3. Open Actions -> CubeBKGSub.
4. Confirm that maskpix contains the selected spectral region.
5. Choose bpsize and bfrad.
6. Apply.

Important parameters:

- bpsize:
  Median-filter box size. It is usually given as three values corresponding to x, y, and spectral dimensions. A common choice is "1 1 45".

- bfrad:
  Filtering radius. A common choice is "0 0 2".

- maskpix:
  Spectral interval excluded from the continuum/background estimate. This should contain the emission line region.

Recommended tests:
Try different background windows, for example:

bpsize = "1 1 20", bfrad = "0 0 2"
bpsize = "1 1 40", bfrad = "0 0 3"
bpsize = "1 1 45", bfrad = "0 0 2"

Then inspect the residual cube and, if needed, produce SNR_F check cubes with CubEx.


3.5 CubeSel - cut the cube around the emission-line region
----------------------------------------------------------
Purpose:
CubeSel extracts a spectral subcube around the emission line of interest. This makes CubEx faster and avoids detecting unrelated emission far away in wavelength.

Typical use:

CubeSel -cube input_cube_BKGSub.fits -zmin 565 -zmax 1113 -out input_cube_BKGSub_sel565_1113.fits

In the GUI:
Actions -> CubeSel

Recommended procedure:

1. Load the background-subtracted cube.
2. Select the spectral interval around the emission line on the spectrum.
3. Open Actions -> CubeSel.
4. Confirm zmin and zmax.
5. Apply.

Important parameters:

- zmin:
  First spectral pixel of the selected region.

- zmax:
  Last spectral pixel of the selected region.

- output file:
  The output cube containing only the selected spectral range.

Important note:
If your cube contains a variance extension or a separate variance cube, apply CubeSel to the variance cube as well, using the same zmin and zmax.


3.6 CreateMask - create a 2D SourceMask from a white-light image
----------------------------------------------------------------
Purpose:
CreateMask runs CubEx on a 2D white-light image to detect continuum/foreground/background sources and create a 2D mask image named SourceMask.fits.

This SourceMask is later used by CubEx to mask contaminating sources while keeping the target source unmasked if needed.

Important:
CreateMask assumes that the 2D image already exists. Therefore, first run Cube2Im to create the white-light image.

Standard sequence:

1. Actions -> Cube2Im
   Create input_cube.IM.fits.

2. Load or select input_cube.IM.fits if desired.

3. Actions -> CreateMask
   Run CubEx on the 2D image.

Equivalent command:

CubEx -cube input_cube.IM.fits -MultiExt .false. -f .true. -fv .true. -fsr 1 -sn 5 -n 80
mv input_cube.IM.Objects_Id.fits SourceMask.fits

Important parameters:

- input_image:
  The white-light image created by Cube2Im.

- output_mask:
  Name of the final source mask. Usually SourceMask.fits.

- MultiExt:
  Usually .false. for a 2D image.

- ApplyFilter:
  Use .true. to smooth/filter the image before source detection.

- ApplyFilterVar:
  Use .true. to apply filtering to the variance/noise estimate.

- FilterXYRad:
  Spatial Gaussian filter radius. Typical value: 1.

- SN_Threshold:
  SNR threshold for source detection in the image. Typical value: 5.

- MinNVox:
  Minimum number of connected pixels/voxels. For 2D source detection, a typical value is 80.

After CreateMask:
Load SourceMask.fits or inspect it externally. Identify the ID number corresponding to the bright central source or any source you want to keep/unmask.


3.7 CubEx - extract the 3D mask of extended emission
----------------------------------------------------
Purpose:
CubEx detects connected 3D emission above a signal-to-noise threshold and produces 3D products such as:

- Objects_Id cube;
- Objects_SNR_F cube;
- catalogue file;
- optional check cubes.

In the standard workflow, CubEx should be run on the continuum-subtracted and spectrally selected cube.

Typical command:

CubEx cubex.par

or with command-line overrides:

CubEx cubex.par -SN_Threshold 2.5 -MinNSpax 100

In the GUI:
Actions -> CubEx

The GUI writes a CubEx parameter file in the same folder as the input cube and then runs CubEx on that parameter file.

Important parameters:

- InpFile:
  Input cube. Usually the continuum-subtracted and spectrally selected cube.

- VarFile:
  Variance file, if not included as extension 2 in the input cube.

- MultiExt:
  If .true., CubEx expects data and variance in different extensions of the same FITS file, unless VarFile is provided.

- ApplyFilter:
  If .true., CubEx applies a Gaussian filter for detection. Photometry is performed on the original cube.

- ApplyFilterVar:
  If .true., the same filter is applied to the variance cube for detection.

- FilterXYRad:
  Spatial Gaussian filter radius in pixels. Typical values: 1-2.

- FilterZRad:
  Spectral Gaussian filter radius in pixels. Typical values: 0-1.

- SN_Threshold:
  Individual voxel SNR threshold for detection. Typical values for faint extended emission: 2-3.

- MinNSpax / MinNVox:
  Minimum number of voxels required for a detection. For compact sources this can be small, while for extended emission one may use values from about 100 to several thousand depending on the science case.

- NCheckCubes:
  Number of check cubes to produce. A useful value is 2.

- CheckCubeType:
  Common useful values are "Objects_Id" and "Objects_SNR_F".

- SourceMask:
  2D mask image used to mask sources before detection. Usually SourceMask.fits.

- UnMask:
  IDs in SourceMask that should not be masked. This is useful when the central target source appears in SourceMask and must be kept.

- XYedge:
  Number of spatial pixels to mask at the cube edges. Useful for noisy boundaries.

- LayerMaskList:
  ASCII file listing spectral layers to mask before extraction. Useful for bad skylines or problematic wavelength regions.

Recommended CubEx strategy:

1. Start with conservative values:
   SN_Threshold = 3
   MinNSpax = 1000
   FilterXYRad = 2
   FilterZRad = 0 or 1

2. Inspect the Objects_Id and Objects_SNR_F cubes.

3. If the nebula is too fragmented or missing, try:
   SN_Threshold = 2.5
   MinNSpax = 100 or 500

4. If too many noisy detections appear, increase:
   SN_Threshold
   MinNSpax
   XYedge

5. Record the final parameter choice in the registry table.

Typical outputs:

input_cube.Objects_Id.fits
input_cube.Objects_SNR_F.fits
input_cube.cat
input_cube_CubEx.par


3.8 Binarize3DMask - keep one or more 3D object IDs and convert them to 1
--------------------------------------------------------------
Purpose:
After CubEx, the Objects_Id cube may contain many detected objects, each with a different integer ID. Binarize3DMask converts one selected object into a binary 3D mask.

Example with one ID:
Binarize3DMask mask3d.fits 60

or

Example with multiple IDs:
Binarize3DMask mask3d.fits 60,61,62


This means:

- voxels with value 60 become 1;
- all other voxels become 0;
- the same FITS file is overwritten.

In the GUI:
Actions -> Binarize3DMask

Important parameters:

- mask3d:
  The CubEx Objects_Id FITS cube.

- selected_id:
  One or more integer IDs of the objects to keep. Multiple IDs can be provided either comma-separated or space-separated, for example 33,56,98 or 33 56 98.

Recommended procedure:

1. Load or inspect the CubEx Objects_Id cube.
2. Identify the ID corresponding to the nebula.
3. Open Actions -> Binarize3DMask.
4. Set mask3d to the Objects_Id cube.
5. Set selected_id to the nebula ID.
6. Apply.
7. Reload the mask if needed.

Output:
The input mask3d file is overwritten and becomes a binary mask with values 0 and 1.

Important warning:
This action overwrites the selected FITS file. If you want to preserve the original Objects_Id cube, make a copy first.


3.9 CreateMaps - generate surface-brightness and kinematic maps
---------------------------------------------------------------
Purpose:
CreateMaps runs Cube2Im twice:

1. to create a surface-brightness / flux map;
2. to create a kinematic / velocity map.

It uses the science cube and a binary 3D mask, usually produced by Binarize3DMask.

Equivalent commands:

Cube2Im -cube CubeBKGout.fits -idcube mask3d.fits -id 1 -idpad IDPAD -out SBmap.fits -nl NL -nlpad NLPAD -imtype "flux" -sbscale .true. -gsm GSM

Cube2Im -cube CubeBKGout.fits -idcube mask3d.fits -id 1 -idpad IDPAD -out KinMap.fits -nlpad NLPAD2 -nl NL2 -imtype "vmap" -sbscale .true. -gsm GSM2 -vzero VZERO -writeNaN .true. -vzerotype lambda

In the GUI:
Actions -> CreateMaps

Important parameters:

- cube:
  Science cube from which the maps are extracted. Usually the background-subtracted and spectrally selected cube.

- mask3d:
  Binary 3D mask. Usually the output of Binarize3DMask.

- SBmap:
  Output surface-brightness or flux map.

- KinMap:
  Output kinematic map.

- id:
  Object ID in the mask. For binary masks, use id = 1.

- idpad:
  Padding around the selected object mask. Typical values: 5-20. Use larger values if the mask is too tight.

- nl:
  Spectral-layer selection for the flux map. Often nl = -1 to use the mask-defined spectral range.

- nlpad:
  Additional spectral padding for the flux map. Typical values: 0-5.

- gsm:
  Gaussian smoothing radius for the flux map. Typical values: 0-2.

- sbscale:
  Use .true. to output a surface-brightness-scaled map.

- nl2:
  Spectral-layer selection for the kinematic map. Often 0 or -1 depending on the desired CubEx behavior.

- nlpad2:
  Additional spectral padding for the kinematic map.

- gsm2:
  Gaussian smoothing radius for the kinematic map. Typical values: 1-2.

- vzero:
  Reference wavelength for the velocity map. This should usually be the expected observed wavelength of the line, for example:

  vzero = lambda_rest * (1 + z)

Examples:

Ly-alpha:
  vzero = 1215.67 * (1 + z)

HeII 1640:
  vzero = 1640.41 * (1 + z)

CIV:
  vzero approximately 1549 * (1 + z)

when this cell is empty the program automatically considers the flux-weighted centroid of the line.

Outputs:

- moment-0 / surface-brightness map;
- kinematic / velocity map.

Suggested filenames:

Target_Line_mom0.fits
Target_Line_mom1.fits


4. Recommended full worked procedure
====================================

This section summarizes a typical reproducible analysis.

Step 0 - Prepare the data
-------------------------
Start from an input datacube, ideally with variance information either in a second extension or in a separate variance file.

Example:

DATACUBE.fits

If the target is a bright QSO or point source, identify the approximate source position.


Step 1 - Load the cube
----------------------
Open AutomatiCubEx.py and load the cube.

Check:

- the cube dimensions;
- the wavelength axis;
- the approximate emission-line region;
- the source position.

Click on the source to store x,y.


Step 2 - Create a white-light image
-----------------------------------
Run:

Actions -> Cube2Im

Input:

cube = DATACUBE.fits
out  = DATACUBE.IM.fits

This image will be used later to identify continuum sources and build SourceMask.fits.


Step 3 - PSF subtraction without mask
-------------------------------------
If needed, run:

Actions -> CubePSFSub

Input:

cube = DATACUBE.fits
out  = DATACUBE_PSFSub.fits
x,y  = source center selected from the GUI
maskpix = empty
zPSFsize = 150
rmin = 1
rmax = 25

Inspect the output cube.


Step 4 - PSF subtraction with mask
----------------------------------
If the emission line is strong or extended, select the spectral region containing the expected emission and rerun CubePSFSub with maskpix set.

Input:

cube = DATACUBE.fits
out  = DATACUBE_PSFSub_masked.fits
maskpix = zmin zmax

This helps avoid subtracting real extended line emission as part of the PSF model.


Step 5 - Background / continuum subtraction
-------------------------------------------
Run:

Actions -> CubeBKGSub

Input:

cube = DATACUBE_PSFSub.fits
out  = DATACUBE_PSFSub_BKGSub.fits
bpsize = "1 1 45"
bfrad  = "0 0 2"
maskpix = zmin zmax

The emission-line spectral region should be masked during continuum estimation.


Step 6 - Select the emission-line subcube
-----------------------------------------
Run:

Actions -> CubeSel

Input:

cube = DATACUBE_PSFSub_BKGSub.fits
zmin = selected lower spectral pixel
zmax = selected upper spectral pixel
out  = DATACUBE_PSFSub_BKGSub_selZMIN_ZMAX.fits

If needed, apply the same cut to the variance cube.


Step 7 - Create a source mask
-----------------------------
First create the white-light image if not already done:

Actions -> Cube2Im

Then run:

Actions -> CreateMask

Input:

input_image = DATACUBE.IM.fits
output_mask = SourceMask.fits
MultiExt = .false.
ApplyFilter = .true.
ApplyFilterVar = .true.
FilterXYRad = 1
SN_Threshold = 5
MinNVox = 80

Inspect SourceMask.fits and identify the ID of the central source or any object that should remain unmasked.


Step 8 - Run CubEx on the emission-line cube
--------------------------------------------
Run:

Actions -> CubEx

Typical parameters:

InpFile = DATACUBE_PSFSub_BKGSub_selZMIN_ZMAX.fits
VarFile = variance cube, if needed
ApplyFilter = .true.
ApplyFilterVar = .true.
FilterXYRad = 2
FilterZRad = 0 or 1
SN_Threshold = 2.5 or 3
MinNSpax = 100-5000
NCheckCubes = 2
CheckCubeType = "Objects_Id" "Objects_SNR_F"
SourceMask = SourceMask.fits
UnMask = ID of the central source to keep, if needed
XYedge = 10 or 20
LayerMaskList = optional list of bad layers

The GUI writes a CubEx parameter file and runs CubEx.

Inspect:

DATACUBE_PSFSub_BKGSub_selZMIN_ZMAX.Objects_Id.fits
DATACUBE_PSFSub_BKGSub_selZMIN_ZMAX.Objects_SNR_F.fits

Identify the object ID corresponding to the extended emission.


Step 9 - Binarize the 3D mask
-----------------------------
Run:

Actions -> Binarize3DMask

Input:

mask3d = DATACUBE_PSFSub_BKGSub_selZMIN_ZMAX.Objects_Id.fits
selected_id = ID of the nebula, or multiple IDs if the nebula is split into several CubEx detections.
Example: selected_id = 33,56,98

After applying, the file becomes a binary mask:

1 = selected nebula
0 = everything else

Make a backup first if you want to preserve the original CubEx IDs.


Step 10 - Generate maps
-----------------------
Run:

Actions -> CreateMaps

Input:

cube = DATACUBE_PSFSub_BKGSub_selZMIN_ZMAX.fits
mask3d = binary 3D mask
SBmap = Target_Line_mom0.fits
KinMap = Target_Line_mom1.fits
id = 1
idpad = 10
nl = -1
nlpad = 3
gsm = 1
sbscale = .true.
nl2 = 0
nlpad2 = 0
gsm2 = 2
vzero = expected observed wavelength

The output maps can then be used for scientific analysis of morphology, surface brightness, and kinematics.


5. Practical recommendations
============================

5.1 Always inspect intermediate products
----------------------------------------
For faint extended emission, do not trust a single automatic run. Inspect:

- original cube;
- PSF-subtracted cube;
- continuum-subtracted cube;
- selected subcube;
- white-light image;
- SourceMask;
- CubEx Objects_Id cube;
- CubEx Objects_SNR_F cube;
- binary 3D mask;
- final moment maps.


5.2 Keep filenames explicit
---------------------------
Use filenames that preserve the analysis history, for example:

DATACUBE_PSFSub.fits
DATACUBE_PSFSub_BKGSub.fits
DATACUBE_PSFSub_BKGSub_sel565_1113.fits
DATACUBE_PSFSub_BKGSub_sel565_1113.Objects_Id.fits
DATACUBE_PSFSub_BKGSub_sel565_1113_Mask3D_binary.fits
Target_Lya_mom0.fits
Target_Lya_mom1.fits


5.3 Save and use the action registry
------------------------------------
Always set an action registry CSV file. This makes the analysis traceable and helps avoid losing the exact parameters used in successful runs.


5.4 Use selected spectral regions carefully
-------------------------------------------
The spectral region selected on the spectrum is used by several actions. Make sure it covers the full expected emission line and includes enough margin for broad or asymmetric emission.

For continuum subtraction, the selected line region should be masked so that real emission does not bias the continuum model.


5.5 Tune CubEx iteratively
--------------------------
Typical first run:

SN_Threshold = 3
MinNSpax = 1000
FilterXYRad = 2
FilterZRad = 0 or 1

If the nebula is missed:

SN_Threshold = 2.5
MinNSpax = 100-500

If too much noise is detected:

SN_Threshold = 3.5 or higher
MinNSpax = larger
XYedge = 10-20
LayerMaskList = use bad-layer mask


5.6 Keep backups before overwriting masks
-----------------------------------------
Binarize3DMask overwrites the selected mask file. Before applying it, copy the original Objects_Id cube if you want to preserve the original CubEx IDs.
If the nebula is split into multiple CubEx IDs, Binarize3DMask can keep all of them at once by passing multiple IDs, for example 33,56,98.

Suggested practice:

copy Objects_Id.fits to Mask3D_original.fits
then run Binarize3DMask on a separate working copy.


5.7 Moment-map interpretation
-----------------------------
The flux map traces the integrated emission selected by the 3D mask.

The kinematic map depends strongly on:

- the mask quality;
- the selected vzero;
- the smoothing parameter gsm2;
- the spectral padding nlpad2;
- the local SNR.

Always compare the kinematic map with the flux map and the Objects_SNR_F cube.


6. Minimal command-line equivalent
==================================

A minimal command-line version of the GUI workflow is:

Cube2Im -cube DATACUBE.fits -out DATACUBE.IM.fits

CubePSFSub -cube DATACUBE.fits -out DATACUBE_PSFSub.fits -x Xsrc -y Ysrc -nbins -1 -zPSFsize 150 -rmin 1 -rmax 25

CubeBKGSub -cube DATACUBE_PSFSub.fits -out DATACUBE_PSFSub_BKGSub.fits -bpsize "1 1 45" -bfrad "0 0 2" -maskpix "ZMIN ZMAX"

CubeSel -cube DATACUBE_PSFSub_BKGSub.fits -zmin ZMIN -zmax ZMAX -out DATACUBE_PSFSub_BKGSub_selZMIN_ZMAX.fits

CubEx -cube DATACUBE.IM.fits -MultiExt .false. -f .true. -fv .true. -fsr 1 -sn 5 -n 80
mv DATACUBE.IM.Objects_Id.fits SourceMask.fits

CubEx cubex.par

Binarize3DMask Objects_Id.fits SELECTED_ID
Binarize3DMask Objects_Id.fits 33,56,98

Cube2Im -cube DATACUBE_PSFSub_BKGSub_selZMIN_ZMAX.fits -idcube Mask3D.fits -id 1 -idpad 10 -out Target_mom0.fits -nl -1 -nlpad 3 -imtype "flux" -sbscale .true. -gsm 1

Cube2Im -cube DATACUBE_PSFSub_BKGSub_selZMIN_ZMAX.fits -idcube Mask3D.fits -id 1 -idpad 10 -out Target_mom1.fits -nl 0 -nlpad 0 -imtype "vmap" -sbscale .true. -gsm 2 -vzero VZERO -writeNaN .true. -vzerotype lambda


7. Troubleshooting
==================

Problem: CubEx or a CubEx Tool is not found.
Solution: Check that Set CubEx path points to the root CubEx directory, not to the Tools directory.

Problem: CreateMask says the input image does not exist.
Solution: Run Cube2Im first to create the white-light image.

Problem: CubEx detects too many noisy regions.
Solution: Increase SN_Threshold, increase MinNSpax, use XYedge, or add a LayerMaskList.

Problem: CubEx misses the nebula.
Solution: Lower SN_Threshold, lower MinNSpax, increase FilterXYRad or FilterZRad carefully, and check whether the emission region was accidentally removed by PSF or continuum subtraction.

Problem: the final maps look too small or clipped.
Solution: Increase idpad and/or nlpad in CreateMaps.

Problem: the velocity map has unexpected zero point.
Solution: Check vzero. It should correspond to the expected observed wavelength of the line.

Problem: the spectrum panel is empty.
Solution: This is expected if a 2D FITS image is loaded. The spectrum panel is used only for 3D cubes.


8. Suggested future improvements
================================

The current GUI already supports a reproducible extended-emission workflow. Useful future developments may include:

- saving and loading full project files;
- storing the current source position, redshift, line name, and vzero automatically;
- adding support for multiple emission lines per target;
- adding direct preview of CubEx Objects_Id labels;
- adding a safer non-destructive Binarize3DMask mode that writes a new file instead of overwriting;
- adding automatic computation of vzero from line name and redshift;
- adding a final FITS/CSV master table of measured nebular quantities.


## Documentation

A complete visual step-by-step guide is available here:

[AutomatiCubEx Visual Guide](docs/AutomatiCubEx_visual_guide.pdf)

