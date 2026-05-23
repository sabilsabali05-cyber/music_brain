# Ableton Export Workflow (v1)

`export-ableton-project-v1` creates an Ableton-ready project scaffold from tangible generation outputs.

## What v1 creates

- A project folder at `outputs/ableton_project_v1/AI_Generated_Song_Project`
- Copied MIDI clips under `MIDI/`
- `track_setup.json` with track roles and clip assignments
- `Ableton_Project_Plan.md` and `Open_In_Ableton_Instructions.md`
- A public-safe `synplant_seed_summary.md` (no private local paths)

## How to use in Ableton

1. Open Ableton Live and create a new Set.
2. Create tracks matching `track_setup.json`.
3. Drag files from `MIDI/` into their tracks.
4. Review `synplant_seed_summary.md` and manually choose source samples.
5. Manually drag selected seeds into Synplant/Ableton if desired.

## Notes on Synplant and sample handling

- Synplant automation is not performed in this workflow.
- Source sample audio is not copied by default.
- If explicitly enabled via `--copy-local-samples`, selected samples can be copied into `Samples/`.
- Private source paths are written only to ignored local files (`private_synplant_seed_paths.*`).

## ALS generation status

- `als_generation_status: not_implemented_experimental_future`
- Direct `.als` generation is future/experimental and is not guaranteed in v1.
- Preferred long-term path is Max for Live-assisted session loading/control.
