# First Training Objectives

Recommended initial order for personalization work (without claiming training has already happened):

1. MusicBERT style evaluator/ranker
   - objective: candidate symbolic output + context -> quality/taste score

2. Synplant seed selector
   - objective: sound candidate + role/context -> seed usefulness score

3. MIDI-GPT style drum/groove variation ranker
   - objective: groove candidate + section context -> useful/not useful

4. Moonbeam adapter/fine tune path
   - objective: context/task -> symbolic continuation/infill

5. Text2MIDI personalization
   - objective: user prompt language -> symbolic sketch

6. Agent workflow preference model
   - objective: tool plan + outcome -> success probability

Notes:
- Start with rankers and preference models where labels are available.
- Keep authorization and policy routing constraints active for every stage.
- Delay full fine tuning until validation and policy controls are stable.
