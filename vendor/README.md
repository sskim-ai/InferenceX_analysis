# Local source provenance

`InferenceX/` is an untracked local full clone of
[`SemiAnalysisAI/InferenceX`](https://github.com/SemiAnalysisAI/InferenceX) pinned to
`3ac9ddfd8161c96ec7e18b1bcfab340369185fcf` (commit subject: `test: prepare complete
HiSparse AgentX sweep`). It is intentionally **not** a Git submodule: this analysis
repository was already being scaffolded, so changing `.gitmodules` and the parent
index would have created unnecessary shared-worktree churn. The requested workflow
and recipe are reproducible from this SHA.

To recreate the local source checkout:

```sh
git clone https://github.com/SemiAnalysisAI/InferenceX.git vendor/InferenceX
git -C vendor/InferenceX checkout --detach 3ac9ddfd8161c96ec7e18b1bcfab340369185fcf
```

The clone's `.git/` directory and upstream source tree are ignored by this analysis
repository. See `manifests/provenance.json` and `reports/01_provenance.md` for the
verified run and recipe evidence.
