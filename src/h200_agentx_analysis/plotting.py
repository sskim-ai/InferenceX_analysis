"""Figure generation that makes missing H200 evidence visually explicit."""

from __future__ import annotations

import json
import os
import textwrap
from collections.abc import Callable
from pathlib import Path

# MPLCONFIGDIR must be set before importing matplotlib.  Keeping its cache in
# /private/tmp avoids writing user-home state during a reproducible run.
_MPL_CACHE = Path("/private/tmp/h200_agentx_mpl")
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


def _read(root: Path, stem: str) -> pd.DataFrame:
    """Read a derived table, treating unavailable/corrupt outputs as unavailable."""

    for path, reader in (
        (root / "data" / "processed" / f"{stem}.parquet", pd.read_parquet),
        (root / "data" / "processed" / f"{stem}.csv", pd.read_csv),
    ):
        if path.exists():
            try:
                return reader(path)
            except Exception:  # figure will carry an explicit unavailable label
                return pd.DataFrame()
    return pd.DataFrame()


def _read_status(root: Path, name: str) -> dict[str, object]:
    path = root / "data" / "processed" / name
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _column(frame: pd.DataFrame, *names: str) -> str | None:
    lower = {str(column).lower(): str(column) for column in frame.columns}
    for name in names:
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def _save_placeholder(path: Path, title: str, reason: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(9, 4.8))
    axis.axis("off")
    axis.set_title(title)
    axis.text(0.5, 0.5, reason, ha="center", va="center", wrap=True, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _save(path: Path, title: str, draw: Callable[[plt.Axes], bool]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(9, 5.2))
    try:
        drawn = draw(axis)
        if not drawn:
            plt.close(fig)
            _save_placeholder(path, title, "No eligible observations are available for this figure.")
            return
        # Several required figures carry both a precise interpretation label
        # and the sample/weighting/concurrency context.  Wrap each supplied
        # line so the right edge is not silently clipped in a PNG.
        wrapped_title = "\n".join(
            "\n".join(textwrap.wrap(line, width=88, break_long_words=False))
            for line in title.splitlines()
        )
        axis.set_title(wrapped_title)
        axis.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(path, dpi=160)
    except Exception as exc:  # Failure must be visible, never silently skipped.
        plt.close(fig)
        _save_placeholder(path, title, f"Figure unavailable: {type(exc).__name__}: {exc}")
        return
    plt.close(fig)


def _scatter_by_concurrency(
    frame: pd.DataFrame,
    x_names: tuple[str, ...],
    y_names: tuple[str, ...],
    axis: plt.Axes,
    x_label: str,
    y_label: str,
) -> bool:
    x = _column(frame, *x_names)
    y = _column(frame, *y_names)
    conc = _column(frame, "concurrency")
    if not x or not y or frame.empty:
        return False
    usable = frame.dropna(subset=[x, y])
    if usable.empty:
        return False
    if conc:
        for value, group in usable.groupby(conc):
            axis.scatter(group[x], group[y], s=10, alpha=0.45, label=f"conc{value}")
        axis.legend(title="concurrency", fontsize=8, ncol=2)
    else:
        axis.scatter(usable[x], usable[y], s=10, alpha=0.45)
    axis.set_xlabel(x_label)
    axis.set_ylabel(y_label)
    return True


def _sample_context(n: int | str, weighting: str, concurrency: str) -> str:
    return f"n={n}; weighting={weighting}; concurrency={concurrency}"


def _rank_metric_subset(frame: pd.DataFrame, rank_metric: str) -> pd.DataFrame:
    """Select the intended ranking block from concatenated top-ID outputs.

    ``top_ids_by_*`` concatenates a separate top-20 block for each metric. A
    chart must filter ``rank_metric`` before selecting the first rows, or a
    wall-time chart can accidentally plot the preceding TTFT-ranked block.
    """

    if frame.empty or "rank_metric" not in frame.columns:
        return frame
    return frame.loc[frame["rank_metric"].astype("string") == rank_metric].copy()


def _cross_concurrency_ratio_groups(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separate actual comparisons from baseline/self and coverage-confounded rows."""

    if frame.empty:
        return frame.copy(), frame.copy()
    data = frame.copy()
    baseline = _column(data, "baseline_concurrency")
    concurrency = _column(data, "concurrency")
    if baseline and concurrency:
        left = pd.to_numeric(data[concurrency], errors="coerce")
        right = pd.to_numeric(data[baseline], errors="coerce")
        data = data.loc[left.ne(right)].copy()
    coverage = _column(data, "coverage_comparable")
    if coverage is None:
        return data.iloc[0:0].copy(), data
    normalized = data[coverage].astype("string").str.strip().str.lower()
    comparable = data.loc[normalized.isin(["true", "1", "yes"])].copy()
    confounded = data.loc[~normalized.isin(["true", "1", "yes"])].copy()
    return comparable, confounded


def _ratio_sample_context(frame: pd.DataFrame, names: tuple[str, ...]) -> str:
    """Describe displayed metric-valid ID comparisons without self ratios."""

    comparable, confounded = _cross_concurrency_ratio_groups(frame)
    metric = _column(frame, *names)
    if metric:
        comparable = comparable.dropna(subset=[metric])
        confounded = confounded.dropna(subset=[metric])
    total = len(comparable) + len(confounded)
    return f"{total} metric-valid; {len(comparable)} comparable; {len(confounded)} coverage-confounded/unknown"


def _numeric_validation_row_count(frame: pd.DataFrame) -> int:
    """Count rows eligible for the numeric raw/published ratio scatter."""

    raw = _column(frame, "recomputed", "raw_value")
    published = _column(frame, "published", "published_value")
    if not raw or not published or frame.empty:
        return 0
    data = frame[[raw, published]].copy()
    data[raw] = pd.to_numeric(data[raw], errors="coerce")
    data[published] = pd.to_numeric(data[published], errors="coerce")
    data = data.replace([np.inf, -np.inf], np.nan).dropna(subset=[raw, published])
    return int((data[published] != 0).sum())


def generate_figures(root: Path) -> list[Path]:
    """Create all required figure files, with blocked placeholders if needed."""

    figures = root / "figures"
    h200 = _read(root, "h200_requests_profiled")
    source = _read(root, "source_trace_summary")
    coverage = _read(root, "id_coverage_matrix")
    summary = _read(root, "id_concurrency_summary")
    ratios = _read(root, "id_concurrency_ratios")
    paired = _read(root, "paired_turn_comparisons")
    exact_cache = _read(root, "exact_turn_cache_shape")
    validation = _read(root, "aggregate_validation")
    numeric_validation_rows = _numeric_validation_row_count(validation)
    top_workload = _read(root, "top_ids_by_workload")
    top_latency = _read(root, "top_ids_by_latency")
    h200_status = _read_status(root, "h200_build_status.json")
    coverage_status = _read_status(root, "coverage_status.json")
    h200_blocked = (
        h200_status.get("status") == "blocked_no_profile_export"
        or coverage_status.get("status") == "blocked_no_profile_export"
    )
    coverage_columns = [column for column in coverage.columns if str(column).lower().startswith("conc")]
    coverage_observed_count = (
        int((coverage[coverage_columns].fillna(0).astype(float) > 0).any(axis=1).sum())
        if coverage_columns
        else 0
    )
    block_reason = (
        "Blocked: `profile_export.jsonl` was not acquired. This is not evidence of zero "
        "H200 observations; authenticate with `gh auth login --web --git-protocol ssh` and rerun `make acquire-run`."
    )
    outputs: list[Path] = []

    def emit(
        name: str,
        title: str,
        draw: Callable[[plt.Axes], bool],
        *,
        n: int | str,
        weighting: str,
        concurrency: str,
        requires_h200: bool = True,
    ) -> None:
        path = figures / name
        full_title = f"{title}\n{_sample_context(n, weighting, concurrency)}"
        if requires_h200 and h200_blocked:
            _save_placeholder(path, full_title, block_reason)
        else:
            _save(path, full_title, draw)
        outputs.append(path)

    def heatmap(axis: plt.Axes) -> bool:
        if coverage.empty:
            return False
        columns = coverage_columns
        if not columns:
            return False
        # The source universe has 393 rows but only a small observed subset.
        # Rendering the first 250 source IDs leaves the informative stripes at
        # the top and makes coverage look blank.  Display the observed union
        # and state the omitted-unobserved denominator in the sample context.
        frame = coverage.loc[(coverage[columns].fillna(0).astype(float) > 0).any(axis=1)].copy()
        if frame.empty:
            return False
        matrix = frame[columns].fillna(0).astype(float).to_numpy()
        axis.imshow(matrix > 0, aspect="auto", interpolation="nearest", cmap="Blues")
        axis.set_xlabel("concurrency")
        axis.set_ylabel(f"observed root trace ID ({len(frame)} shown)")
        axis.set_xticks(range(len(columns)), columns)
        trace_id = _column(frame, "root_trace_id")
        if trace_id:
            axis.set_yticks(range(len(frame)))
            axis.set_yticklabels([str(value)[:10] for value in frame[trace_id]], fontsize=7)
        else:
            axis.set_yticks([])
        return True

    emit(
        "id_coverage_heatmap.png",
        "Observed profiling ID coverage by concurrency",
        heatmap,
        n="unknown (blocked)" if h200_blocked else f"{coverage_observed_count}/{len(coverage)} observed root IDs",
        weighting="root-ID presence",
        concurrency="conc1–8",
    )

    def source_size(axis: plt.Axes) -> bool:
        if source.empty or coverage.empty:
            return False
        key = _column(source, "root_trace_id")
        tokens = _column(source, "source_total_input_tokens", "total_input_tokens")
        coverage_key = _column(coverage, "root_trace_id")
        conc_columns = [column for column in coverage.columns if str(column).lower().startswith("conc")]
        if not key or not tokens or not coverage_key or not conc_columns:
            return False
        present = coverage[[coverage_key, *conc_columns]].copy()
        present["observed_probability"] = (present[conc_columns].fillna(0) > 0).mean(axis=1)
        joined = source.merge(present[[coverage_key, "observed_probability"]], left_on=key, right_on=coverage_key)
        joined = joined.dropna(subset=[tokens, "observed_probability"])
        if joined.empty:
            return False
        axis.scatter(joined[tokens], joined["observed_probability"], s=12, alpha=0.55)
        axis.set_xscale("symlog", linthresh=1)
        axis.set_xlabel("source total input tokens (symlog)")
        axis.set_ylabel("observation probability across conc1–8")
        return True

    emit(
        "coverage_by_source_trace_size.png",
        "Source trace size vs H200 observation probability",
        source_size,
        n="unknown (blocked)" if h200_blocked else len(source),
        weighting="source root-ID",
        concurrency="conc1–8",
    )
    emit(
        "isl_vs_ttft_by_concurrency.png",
        "Input sequence length vs observed H200 replay TTFT (ms)",
        lambda axis: _scatter_by_concurrency(
            h200,
            ("input_tokens", "input_sequence_length"),
            ("ttft_ms", "time_to_first_token"),
            axis,
            "input tokens",
            "TTFT (ms)",
        ),
        n="unknown (blocked)" if h200_blocked else len(h200),
        weighting="profiling request",
        concurrency="all observed",
    )
    emit(
        "theoretical_new_tokens_vs_ttft.png",
        "Theoretical new source tokens vs observed H200 replay TTFT (ms); exact joins only",
        lambda axis: _scatter_by_concurrency(
            exact_cache,
            ("theoretical_new_tokens",),
            ("ttft_ms", "h200_ttft_ms"),
            axis,
            "theoretical new tokens",
            "TTFT (ms)",
        ),
        n="unknown (blocked)" if h200_blocked else len(exact_cache),
        weighting="exact-turn request",
        concurrency="all observed",
    )

    def itl_distribution(axis: plt.Axes) -> bool:
        metric = _column(h200, "itl_ms", "inter_token_latency")
        conc = _column(h200, "concurrency")
        if not metric or not conc or h200.empty:
            return False
        groups = [(f"c{key}", group[metric].dropna().to_numpy()) for key, group in h200.groupby(conc)]
        groups = [(name, values) for name, values in groups if len(values)]
        if not groups:
            return False
        axis.boxplot([values for _, values in groups], tick_labels=[name for name, _ in groups], showfliers=False)
        axis.set_xlabel("concurrency")
        axis.set_ylabel("request-level ITL / TPOT (ms)")
        return True

    emit(
        "itl_distribution_by_concurrency.png",
        "Observed H200 replay ITL / TPOT distribution (ms)",
        itl_distribution,
        n="unknown (blocked)" if h200_blocked else int(h200["itl_ms"].notna().sum()),
        weighting="ITL-valid profiling request",
        concurrency="all observed",
    )

    def source_origin_metric_n(metric_names: tuple[str, ...]) -> int | str:
        """Describe only metric-valid source-origin rows for a box plot."""

        metric = _column(h200, *metric_names)
        branch = _column(h200, "source_branch_type")
        if not metric or not branch or h200.empty:
            return "unknown"
        data = h200.loc[
            h200[branch].astype("string").str.strip().str.lower().isin(["root", "subagent"])
            & h200[metric].notna()
        ].copy()
        counts = data[branch].astype("string").str.strip().str.lower().value_counts()
        return f"{len(data)} metric-valid (root={int(counts.get('root', 0))}; subagent={int(counts.get('subagent', 0))})"

    def source_origin_box(
        metric_names: tuple[str, ...], label: str
    ) -> Callable[[plt.Axes], bool]:
        def draw(axis: plt.Axes) -> bool:
            metric = _column(h200, *metric_names)
            branch = _column(h200, "source_branch_type")
            if not metric or not branch or h200.empty:
                return False
            data = h200.copy()
            data[branch] = data[branch].astype("string").str.strip().str.lower()
            # This graph answers the source-root versus source-nested-agent
            # question. H200 replay suffix categories are intentionally not
            # substituted here: e.g. a replay fanout can be a source root.
            data = data.loc[data[branch].isin(["root", "subagent"])]
            groups = [
                (str(key), group[metric].dropna().to_numpy()) for key, group in data.groupby(branch)
            ]
            groups = [(name, values) for name, values in groups if len(values)]
            if not groups:
                return False
            axis.boxplot([values for _, values in groups], tick_labels=[name for name, _ in groups], showfliers=False)
            axis.tick_params(axis="x", rotation=20)
            axis.set_ylabel(label)
            return True

        return draw

    emit(
        "root_vs_subagent_ttft.png",
        "Source-root vs source-nested-subagent origin: observed H200 replay TTFT (ms)",
        source_origin_box(("ttft_ms",), "TTFT (ms)"),
        n="unknown (blocked)" if h200_blocked else source_origin_metric_n(("ttft_ms",)),
        weighting="TTFT-valid profiling request; source-origin branch type",
        concurrency="all observed",
    )
    emit(
        "root_vs_subagent_itl.png",
        "Source-root vs source-nested-subagent origin: observed H200 replay ITL / TPOT (ms)",
        source_origin_box(("itl_ms",), "ITL / TPOT (ms)"),
        n="unknown (blocked)" if h200_blocked else source_origin_metric_n(("itl_ms",)),
        weighting="ITL-valid profiling request; source-origin branch type",
        concurrency="all observed",
    )

    def ratio_plot(names: tuple[str, ...], label: str) -> Callable[[plt.Axes], bool]:
        def draw(axis: plt.Axes) -> bool:
            ratio = _column(ratios, *names)
            conc = _column(ratios, "concurrency")
            if not ratio or ratios.empty:
                return False
            comparable, confounded = _cross_concurrency_ratio_groups(ratios)
            comparable = comparable.dropna(subset=[ratio])
            confounded = confounded.dropna(subset=[ratio])
            if comparable.empty and confounded.empty:
                return False
            if conc:
                for key, group in comparable.groupby(conc):
                    axis.scatter(
                        np.full(len(group), float(key)),
                        group[ratio],
                        alpha=0.7,
                        s=20,
                        color="C0",
                        label="coverage-comparable",
                    )
                for key, group in confounded.groupby(conc):
                    axis.scatter(
                        np.full(len(group), float(key)),
                        group[ratio],
                        alpha=0.65,
                        s=28,
                        color="0.45",
                        marker="x",
                        label="coverage-confounded/unknown",
                    )
                axis.set_xlabel("comparison concurrency")
            else:
                axis.scatter(
                    range(len(comparable)),
                    comparable[ratio],
                    alpha=0.7,
                    s=20,
                    color="C0",
                    label="coverage-comparable",
                )
                axis.scatter(
                    range(len(comparable), len(comparable) + len(confounded)),
                    confounded[ratio],
                    alpha=0.65,
                    s=28,
                    color="0.45",
                    marker="x",
                    label="coverage-confounded/unknown",
                )
            axis.axhline(1, color="black", linewidth=1, linestyle="--")
            axis.set_ylabel(label)
            handles, labels = axis.get_legend_handles_labels()
            if handles:
                by_label = dict(zip(labels, handles, strict=False))
                axis.legend(by_label.values(), by_label.keys(), fontsize=8)
            return True

        return draw

    emit(
        "concurrency_vs_ttft_by_id.png",
        "ID-level TTFT ratio: cross-concurrency comparisons by coverage status",
        ratio_plot(("ttft_ratio", "median_ttft_ratio"), "TTFT ratio"),
        n="unknown (blocked)" if h200_blocked else _ratio_sample_context(ratios, ("ttft_ratio", "median_ttft_ratio")),
        weighting="root-ID summary",
        concurrency="baseline vs conc1–8",
    )
    emit(
        "concurrency_vs_itl_by_id.png",
        "ID-level ITL / TPOT ratio: cross-concurrency comparisons by coverage status",
        ratio_plot(("itl_ratio", "median_itl_ratio"), "ITL ratio"),
        n="unknown (blocked)" if h200_blocked else _ratio_sample_context(ratios, ("itl_ratio", "median_itl_ratio")),
        weighting="root-ID summary",
        concurrency="baseline vs conc1–8",
    )

    def top_bar(
        frame: pd.DataFrame, candidates: tuple[str, ...], axis: plt.Axes, label: str
    ) -> bool:
        identity = _column(frame, "root_trace_id")
        metric = _column(frame, *candidates)
        if not identity or not metric or frame.empty:
            return False
        data = frame.dropna(subset=[metric]).nlargest(20, metric).iloc[::-1]
        if data.empty:
            return False
        conc = _column(data, "concurrency")
        labels = data[identity].astype(str).str.slice(0, 10)
        if conc:
            labels = labels + " · c" + data[conc].astype("Int64").astype(str)
        positions = np.arange(len(data))
        # Use numeric positions rather than categorical labels: the same root
        # ID can legitimately appear at multiple concurrency points, and
        # categorical barh would otherwise overplot those top-20 rows.
        axis.barh(positions, data[metric])
        axis.set_yticks(positions, labels)
        axis.tick_params(axis="y", labelsize=7)
        axis.set_xlabel(label)
        return True

    emit(
        "top_20_ids_by_total_input_tokens.png",
        "Top 20 observed root-ID × concurrency rows by total input tokens",
        lambda axis: top_bar(
            _rank_metric_subset(top_workload, "total_input_tokens")
            if not top_workload.empty
            else summary,
            ("total_input_tokens",),
            axis,
            "total input tokens",
        ),
        n=(
            "unknown (blocked)"
            if h200_blocked
            else min(20, len(_rank_metric_subset(top_workload, "total_input_tokens") if not top_workload.empty else summary))
        ),
        weighting="root-ID summary",
        concurrency="all observed",
    )
    emit(
        "top_20_ids_by_h200_wall_time.png",
        "Top 20 observed root-ID × concurrency rows by summed request-level H200 wall time (s)",
        lambda axis: top_bar(
            _rank_metric_subset(top_latency, "total_h200_wall_time_s")
            if not top_latency.empty
            else summary,
            ("total_h200_wall_time_s",),
            axis,
            "summed request-level H200 wall time (s)",
        ),
        n=(
            "unknown (blocked)"
            if h200_blocked
            else min(
                20,
                len(
                _rank_metric_subset(top_latency, "total_h200_wall_time_s")
                if not top_latency.empty
                else summary
                ),
            )
        ),
        weighting="root-ID summary",
        concurrency="all observed",
    )

    def paired_hist(names: tuple[str, ...], label: str) -> Callable[[plt.Axes], bool]:
        def draw(axis: plt.Axes) -> bool:
            column = _column(paired, *names)
            if not column or paired.empty:
                return False
            values = paired[column].dropna()
            if values.empty:
                return False
            axis.hist(values, bins=min(40, max(8, int(np.sqrt(len(values))))), alpha=0.8)
            axis.axvline(1, color="black", linewidth=1, linestyle="--")
            axis.set_xlabel(label)
            axis.set_ylabel("paired-turn count")
            return True

        return draw

    emit(
        "paired_ttft_ratio_distribution.png",
        "Paired exact-turn TTFT ratio distribution",
        paired_hist(("ttft_ratio",), "TTFT ratio"),
        n="unknown (blocked)" if h200_blocked else len(paired),
        weighting="exact-turn pair",
        concurrency="actual cross-concurrency pairs",
    )
    emit(
        "paired_itl_ratio_distribution.png",
        "Paired exact-turn ITL / TPOT ratio distribution",
        paired_hist(("itl_ratio",), "ITL ratio"),
        n="unknown (blocked)" if h200_blocked else len(paired),
        weighting="exact-turn pair",
        concurrency="actual cross-concurrency pairs",
    )

    def duration_wall(axis: plt.Axes) -> bool:
        if source.empty or summary.empty:
            return False
        key = _column(source, "root_trace_id")
        duration = _column(source, "source_recorded_span_s")
        summary_key = _column(summary, "root_trace_id")
        wall = _column(summary, "wall_span_s")
        if not key or not duration or not summary_key or not wall:
            return False
        # ``source_recorded_span_s`` is also carried into the ID summary.
        # Select and rename the two intended inputs before merging, otherwise
        # pandas suffixes both copies and an unsuffixed lookup fails.
        source_duration = source[[key, duration]].rename(
            columns={key: "_source_root_trace_id", duration: "_source_recorded_span_s"}
        )
        summary_wall = summary[[summary_key, wall]].rename(
            columns={summary_key: "_summary_root_trace_id", wall: "_h200_wall_span_s"}
        )
        joined = source_duration.merge(
            summary_wall,
            left_on="_source_root_trace_id",
            right_on="_summary_root_trace_id",
        ).dropna(subset=["_source_recorded_span_s", "_h200_wall_span_s"])
        if joined.empty:
            return False
        axis.scatter(joined["_source_recorded_span_s"], joined["_h200_wall_span_s"], s=12, alpha=0.5)
        axis.set_xlabel("source recorded trace span (s)")
        axis.set_ylabel("H200 replay wall span (s)")
        return True

    emit(
        "trace_duration_vs_h200_wall_span.png",
        "Source trace duration vs H200 replay wall span (s)",
        duration_wall,
        n="unknown (blocked)" if h200_blocked else len(summary),
        weighting="root-ID summary",
        concurrency="all observed",
    )

    def validation_plot(axis: plt.Axes) -> bool:
        metric = _column(validation, "metric")
        raw = _column(validation, "recomputed", "raw_value")
        published = _column(validation, "published", "published_value")
        if not metric or not raw or not published or validation.empty:
            return False
        # Categorical provenance checks (model/precision/framework) belong in
        # the validation table but cannot share a numeric plot with latency,
        # token counts, and throughput.  Plot a dimensionless ratio only for
        # numeric comparisons with a non-zero published denominator.
        data = validation[[metric, raw, published]].copy()
        data[raw] = pd.to_numeric(data[raw], errors="coerce")
        data[published] = pd.to_numeric(data[published], errors="coerce")
        data = data.replace([np.inf, -np.inf], np.nan).dropna(subset=[raw, published])
        data = data.loc[data[published] != 0].copy()
        if data.empty:
            return False
        data["raw_to_published_ratio"] = data[raw] / data[published]
        axis.scatter(range(len(data)), data["raw_to_published_ratio"], s=22, alpha=0.7)
        axis.axhline(1, color="black", linestyle="--")
        axis.set_xlabel("numeric aggregate comparison row")
        axis.set_ylabel("recomputed / published (unitless ratio)")
        return True

    emit(
        "aggregate_raw_vs_published_validation.png",
        "Aggregate validation: raw recomputation / published value ratio",
        validation_plot,
        n=(
            "unknown (blocked)"
            if h200_blocked
            else f"{numeric_validation_rows} numeric rows ({len(validation) - numeric_validation_rows} categorical checks in table)"
        ),
        weighting="aggregate metric",
        concurrency="all observed",
    )
    return outputs
