# Muronto Demo Walkthrough

Muronto is a Streamlit app for connecting to a LabArchives ELN notebook and
recording neuro-behavior experiment records as structured JSON attachments.
This guide is meant as a live demo script for a collaborator, with the main
features arranged in the order they appear in the app.

## Demo Setup

Run the app from the project root:

```bash
uv sync
uv run streamlit run Project.py
```

Before launching, make sure LabArchives API access is configured in the shell
environment:

```bash
export ACCESS_KEYID="..."
export ACCESS_PWD="..."
```

`API_URL` is optional. If it is not set, the app defaults to
`https://api.labarchives.com`. Note this is NOT the url for
the NIH version of LabArchives.

For the demo, use a LabArchives account that can access at least one notebook.
The app does not ask for a LabArchives username, password, email address, auth
token, or `.env` file. Users authenticate through the LabArchives browser
sign-in flow.

## Suggested Demo Path

1. Start on the Project page and show the Muronto landing header.
2. Click `Open LabArchives sign-in`, complete LabArchives authentication, and
   return to the app through the browser callback.
3. Select a notebook and point out the accessible notebook count and default
   notebook display.
4. Create or load the root-level `muronto_config` page.
5. Create or edit a project, select or create its LabArchives home folder, and
   save the config JSON.
6. Show the active project summary and the expandable config JSON.
7. Open the Subject page, create a subject record, and show the generated
   subject JSON.
8. Open the Surgery page, select the subject, fill out one procedure, add a
   note or photo attachment if useful, and save the surgery record.
9. Return to LabArchives and show where the config, subject, surgery JSON, and
   supporting attachments were written.
10. Return to the Project page and demonstrate `Sign out`.

## Project Page Features

The Project page is the required starting point. It manages authentication,
notebook selection, and the shared project configuration used by the Subject
and Surgery pages.

### LabArchives Sign-In

- The app reads API client credentials from `ACCESS_KEYID` and `ACCESS_PWD`.
- The sign-in button opens the LabArchives browser authentication flow.
- LabArchives redirects back with callback parameters, and the app completes
  login automatically.
- If credentials or the callback fail, the page shows a clear error message.
- `Sign out` closes the LabArchives client, clears session state, and returns
  the user to the login flow.

### Notebook Selection

- After login, the app lists notebooks available to the signed-in user.
- The default LabArchives notebook is shown separately.
- Changing notebooks clears project-specific state so the selected notebook and
  config stay aligned.

### `muronto_config`

- The app looks for a root-level LabArchives page named `muronto_config`.
- If the page is missing, the Project page can create it.
- The config is stored as a JSON attachment named `muronto_config.json` with
  the `muronto_config` caption.
- Current configs use schema version 2 and support multiple projects per
  notebook.
- Missing, invalid, or legacy single-project config attachments are surfaced in
  the UI and can be replaced by saving a new v2 config.

### Project Management

- A project includes project ID, project name, LabArchives home folder, PI,
  species, and ASP.
- The project ID is fixed after creation when editing an existing project.
- PI, species, ASP, and investigator fields use reusable option lists plus an
  `Other` choice for new values.
- The selected investigator can be remembered for the signed-in LabArchives
  email.
- The selected project is remembered for the signed-in LabArchives email.
- A project can be set as the notebook default project.
- The active project selector chooses from configured projects and drives the
  Subject and Surgery pages.

### Home Folder Picker

- The home folder picker browses LabArchives folders from the selected
  notebook.
- Breadcrumb buttons navigate back up the folder path.
- `Select this folder` records the current folder as the project's home folder.
- `Create and select folder` creates a child folder and immediately selects it.
- The Subject and Surgery pages use the active project's home folder as their
  LabArchives workspace.

## Subject Page Features

The Subject page requires a signed-in Project page session, a selected
notebook, and a ready `muronto_config`.

### Project Context

- The page repeats the signed-in user, notebook, project ID, project name, home
  folder, investigator, species, and ASP.
- If any required context is missing, the page links back to the Project page.

### Subject Form

- `animal_id` must match `\d\d\d-\d\d\d\d`, for example `123-4567`.
- `ear_tag` must match `\d\d\d`, for example `123`.
- `ccn` must match `\d\d\d\d\d\d`, for example `123456`.
- `sex` is selected from `M` or `F`.
- Strain and genotype are entered as one or more pairs.
- `Add strain/genotype` adds another strain/genotype row.
- Genotype choices are `WT`, `Het`, `Homo`, and `Tg`.
- `dob` and `dow` are selected as dates and saved as `YYYYMMDD`.
- `source_type` uses configured options plus `Other`.
- `parent_ccn` is required for `Breeding` source type and optional otherwise,
  but must match the CCN pattern if provided.

### Subject Save Behavior

- `Create subject page` validates the form before writing anything.
- The app creates a LabArchives page named after the `animal_id` inside the
  active project's home folder.
- Duplicate LabArchives child names in that folder are blocked.
- The app attaches a flat subject JSON payload as `<animal_id>.json` with the
  `muronto_subject` caption.
- Custom strain and source type values are saved back to `muronto_config` so
  they are available in future forms.
- After saving, the app shows the created page name and an expandable Subject
  JSON preview.

## Surgery Page Features

The Surgery page also requires the Project page context. It records surgery
metadata on an existing subject page.

### Subject Discovery

- The page resolves the active project's LabArchives home folder.
- It recursively discovers subject pages that have a valid `muronto_subject`
  JSON attachment.
- Subjects are listed by animal ID and ear tag.
- Selecting a subject displays key subject fields and all recorded
  strain/genotype pairs.

### Surgery Details

- Surgeon uses configured options plus `Other`.
- Surgery date is selected from a date picker and saved as `YYYYMMDD`.
- PreOp CNN and PostOp CNN must match `\d\d\d\d\d\d`.
- Project ID, investigator, animal ID, and ear tag are copied into the surgery
  payload from the active project and selected subject.

### Perioperative Monitoring And Medications

- The form records pre- and post-surgery weights in grams.
- `Add medication` adds medication rows.
- Each medication records medication name, concentration in mg/ml, and volume
  in ml.
- Start and end times are saved as zero-padded `HHMM`.
- The end time must be later than the start time.
- Bregma-lambda distance is recorded in mm.

### Surgical Procedures

- `Add surgical procedure` adds another procedure block.
- Each procedure is either `Viral Injection` or `Implant`.
- Viral injection procedures support multiple injections.
- Each injection records site, hemisphere, one or more viruses, and infusion
  locations.
- Virus records include source, ID, stock, stock titer, dilution, and infusion
  rate. Stock titer must match `\d_\d\d_\d\d`, for example `2_10_13`.
- Infusion locations record AP, ML, DV, infusion volume, post-infusion flow
  test, and notes.

Implant procedures support these detailed implant forms:

- `Cranial Window`: headplate type, coverslip type, coverslip diameter,
  coverslip thickness, region, center AP, center ML, well type, and notes.
- `Crystal Skull`: headplate type, CS type, front AP, left ML, and well type.
- `Electrode`: one or more electrodes with electrode type, probe model, probe
  ID, site, hemisphere, pitch, yaw, roll, AP, ML, DV, ground, reference, and
  notes.

`GRIN Lens` and custom implant types can be selected, but detailed fields are
not implemented yet. The page shows an informational message for unsupported
implant types.

### Notes And Attachments

- General surgery notes are saved into the surgery JSON.
- Note uploads accept multiple files.
- Photo uploads accept common image formats.
- `Add photo` creates camera capture inputs for taking one or more photos from
  the browser.
- Uploaded notes, uploaded photos, and camera captures are saved as
  LabArchives attachments on the selected subject page.
- Supporting attachment references are included in the surgery JSON with upload
  type, entry ID, filename, caption, and MIME type.

### Surgery Save Behavior

- `Save surgery record` validates the complete form before saving the JSON.
- Support files are saved first so their attachment references can be included
  in the final surgery payload.
- The surgery JSON is saved on the selected subject page as
  `<animal_id>_surgery_<YYYYMMDD>.json` with the `muronto_surgery` caption.
- Saving a surgery record for the same animal ID and surgery date updates the
  existing surgery JSON attachment.
- A new animal ID/date combination creates a new surgery JSON attachment.
- Custom surgeon, medication, site, virus, virus source, headplate, coverslip,
  cranial window region, CS type, crystal skull well type, probe model, and
  electrode site values are saved back to `muronto_config` for reuse.
- After saving, the app shows whether the surgery record was created or
  updated and displays the final Surgery JSON.

## What Gets Written To LabArchives

- Root notebook page: `muronto_config`.
- Config attachment: `muronto_config.json`, caption `muronto_config`.
- Subject page: one page per animal ID inside the active project home folder.
- Subject attachment: `<animal_id>.json`, caption `muronto_subject`.
- Surgery attachment: `<animal_id>_surgery_<YYYYMMDD>.json`, caption
  `muronto_surgery`.
- Surgery support attachments: note files, uploaded photos, and camera captures
  saved with caption `muronto_surgery_attachment`.

## Good Demo Values

Use values that will not collide with existing LabArchives pages in the demo
home folder. Example patterns:

- Animal ID: `123-4567`
- Ear tag: `123`
- CCN, PreOp CNN, PostOp CNN, Parent CCN: six digits such as `123456`
- DOB, DOW, and surgery date: choose from the date pickers
- Stock titer: `2_10_13`
- Viral injection coordinates: AP `1.0`, ML `2.0`, DV `-3.0`
- Infusion volume: `100`
- Medication concentration and volume: `5.0` mg/ml and `0.1` ml

## Demo Notes

- The Project page must be configured first because the Subject and Surgery
  pages read active notebook, config, project, and investigator state from the
  Streamlit session.
- The app is intentionally LabArchives-backed. The most useful demo close is
  to switch to LabArchives and show the actual pages and attachments that were
  created or updated.
- Because reusable option values are written back to `muronto_config`, the demo
  can show that custom values entered with `Other` become first-class choices
  the next time the form is opened.
