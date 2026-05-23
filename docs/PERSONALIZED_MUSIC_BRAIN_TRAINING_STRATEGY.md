# Personalized Music Brain Training Strategy

## Core principle

Pretrained base models are allowed, but the end state is personalization from authorized user data:

- user approved symbolic corpus
- review queue decisions
- Ableton arrangement feedback
- Synplant seed and patch outcomes
- sound library choices with explicit authorization
- prompt language preferences
- workflow/tool routing feedback

No training is claimed in this strategy. This document defines what must be collected and validated before training.

## System by system strategy

### Moonbeam

- pretrained role: main symbolic composition, continuation, infill backend
- user personalization path: retrieval conditioned prompting first, then adapter tuning on accepted continuation and infill outcomes
- required training data: symbolic corpus, continuation/infill tasks, acceptance labels, quality scores
- blocked data: unauthorized material, policy unknown items, blocked sources
- first trainable objective: task conditioned continuation quality ranker/controller
- later objective: LoRA fine tune for user style continuation and infill
- validation: holdout continuation quality, policy compliance checks

### MusicBERT

- pretrained role: symbolic understanding, evaluation, similarity, ranking
- user personalization path: classifier/ranker heads trained from accepted vs rejected candidates and similarity judgments
- required training data: symbolic candidates with context, review labels, ranking labels
- blocked data: unauthorized records, blocked sources
- first trainable objective: candidate quality and taste ranker
- later objective: embedding alignment to user similarity preferences
- validation: ranking metrics, leakage checks, human agreement

### MIDI-GPT

- pretrained role: controllable multitrack variation backend
- user personalization path: ranker/controller tuning for drums, groove, density, and track level infill behavior
- required training data: multitrack examples, control labels, groove acceptance labels
- blocked data: unauthorized or blocked sources
- first trainable objective: groove and drum usefulness ranker
- later objective: adapter tune control interpretation to user preference
- validation: control consistency, role integrity, acceptance lift

### Text2MIDI

- pretrained role: prompt to MIDI sketch backend
- user personalization path: prompt language to sketch preference learning from accepted/rejected prompt outputs
- required training data: prompt/sketch pairs, rejection reasons, accepted outputs
- blocked data: unauthorized content
- first trainable objective: prompt conditioned sketch ranker
- later objective: LoRA prompt vocabulary alignment
- validation: prompt style holdout and manual semantic match review

### Texture and Synplant related systems

#### texture_embedding

- pretrained role: texture representation and context fit
- personalization path: fit/ranking from texture metadata, role labels, context fit decisions
- required data: texture fingerprints, role labels, context fit ratings
- blocked data: blocked sources and unknown authorization
- first objective: role/context fit ranker
- later objective: embedding fine tune for personalized retrieval
- validation: retrieval precision and role confusion analysis

#### synplant_seed_selector

- pretrained role: seed selection assistant
- personalization path: rank seed usefulness per role/context from session outcomes
- required data: authorized seed records, context metadata, user ratings
- blocked data: blocked sources, policy violations
- first objective: seed usefulness ranker
- later objective: policy aware selector model
- validation: policy inheritance audit and rating agreement

#### synplant_patch_ranker

- pretrained role: patch outcome ranking
- personalization path: learn keep/reject ranking from manual patch outcomes and ratings
- required data: patch candidates, render refs, ratings
- blocked data: policy violating derivative records
- first objective: patch quality ranker
- later objective: patch preference model
- validation: top-k keep rate and inheritance compliance

#### puredata_texture_planner

- pretrained role: texture planning and routing suggestions
- personalization path: rank plans using accepted arrangement outcomes and review notes
- required data: plan logs, arrangement feedback
- blocked data: unauthorized upstream records
- first objective: plan acceptance ranker
- later objective: multi section texture sequence model
- validation: manual plan review and safety policy checks

### Ableton and controller systems

#### ableton_arrangement_agent

- pretrained role: arrangement guidance and section placement
- personalization path: preference learning from accepted/rejected arrangement revisions
- required data: arrangement decisions, review feedback, final accepted versions
- blocked data: unauthorized assets
- first objective: transition and placement ranker
- later objective: arrangement planner fine tune
- validation: holdout acceptance rate and manual review

#### overall_agent_controller

- pretrained role: workflow and tool routing controller
- personalization path: preference model from tool traces, failures, successful outcomes, and user feedback
- required data: tool traces, workflow feedback, accepted final outputs
- blocked data: unknown authorization events in training route
- first objective: workflow success predictor
- later objective: trajectory preference model for routing
- validation: regression suites, safety audits, reduced manual overrides
