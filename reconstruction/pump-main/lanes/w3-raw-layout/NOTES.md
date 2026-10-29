# Lane w3-raw-layout (wave 3): whole-program raw layout

Base: origin/main 665499915 (1022 normalized / 276 raw; 13 unmatched windows, no ours-only units,
`.text` 0x1b5600 vs original 0x1b58d0, i.e. -720 B, all from the 13 size deltas).

Tools (`tools/`, build on layout-order-census's `fastmodel.py`/`moves.py`/`refine.py`):

| tool | what |
| --- | --- |
| `m13.py` | model helpers for the 13-unmatched world: `p13` (raw once the 13 match in size and code, data equal), `datamap`/`p13real` (same, but a window with data lddw counts only if every data operand already points at the original's in-section offset), `aligned` |
| `metrics.py` | one-line metric set for a build: model raw, P13, P13 with real data, P13 under the original L order / full original order, data-offset-equal windows, LIS / L breaks |
| `trial.sh` | fastbuild + score.py (vs the wave-3 base) + refine + metrics |
| `capture.py` | experiment-only `--emit link,obj,llvm-ir` capture (pass `-C no-prepopulate-passes` for pre-opt IR) |
| `irglob.py` | IR global order vs first-referencing function (nested refs propagated) |
| `ldiff13.py`, `lisL.py`, `prefix.py`, `plan.py`, `scen.py`, `unm.py`, `sites.py` | L-order diff, non-LIS units with their Source sites, prefix model, move plans, scenario ceilings, size deltas, sites per window |

## Ceilings on the base (model reproduces the official 276 exactly)

| scenario | raw |
| --- | ---: |
| today's sizes, original L order | 276 (no gain left) |
| today's sizes, original U / D / U+D order | 279 / 290 / 293 |
| P13 (13 fixed, our order) | 416 |
| P13 with L in original order | 654 |
| P13 with full original order | 1018 |
| P13 full order, data operands as built | 683 (base) |

U and D hash order cannot be reached from source: D-block within-crate order is fixed by the
dependency crates' own metadata (registry crates, independent of `programs/pump`), and U by the
root and anchor StableCrateIds, which depend on the cargo/rustc environment.

## Mechanism: .rodata order is rustc codegen order

Pre-optimization IR (`capture.py ... -C no-prepopulate-passes`) shows every non-merged constant
(`.rodata..Lalloc_*`, statics) is created when the first function referencing it is codegen'd, and
functions are codegen'd in mono-item order: local items by def index, `#[inline]` local functions
included (they are still mono items at their def position; LLVM drops them later). Statics are
emitted at their own def position. Macro-expanded items (`declare_id!`, `declare_program!`) get
def indices in expansion order, after hand-written items and derives.

## Kept changes (all line-neutral, official 1022/276, zero losses)

| trial | change | data-offset-equal windows | rodata bytes aligned |
| --- | --- | ---: | ---: |
| base | | 683 | 31680 / 32031 |
| t01 `c1bc56ca` | mount `buy.rs` (legacy_buy, keeps `#[inline]`) second, after `account_name`; its `native_payments` submodule becomes the top-level `legacy_native_payments` mount at the old position (`pub use ... as native_payments` keeps paths). The original stream has `buy.rs` + `bonding-curve` right after `anchor:idl`. Also fixes the cst4 swap at 0x3bc | 701 | 31709 |
| t02 `aec0dd50` | `declare_id!` (pump ID) moved before `declare_program!(pump_amm)`; MAYHEM_ID is a `declare_id!` static in `mod mayhem_program` after `declare_program!(pump_fees)` (create_v2 re-exports it). Original stream: pump ID before the pump_amm IDs, MAYHEM_ID right after pump_fees' `Global` | 871 | 31772 |

The previous lane's "drop `#[inline]` on legacy buy_exact_sol_in" dead end is not needed: the def
position alone moves the constants, and 0x14f4e0 stays matched.
