#!/bin/bash/env python3

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import patches
from natsort import natsorted
import plotly.graph_objects as go
import pandas as pd


def plot_acr_static(seg_df, ax, csize,
                    segment_colors=None, sigmas=None, min_seg_lw=None, y_upper_lim=None):
    """Create static Allelic Copy Ratio plot for given segment profile.

    :param seg_df: pandas.DataFrame with segment profile (allelic CN mu and sigmas)
    :param ax: matplotlib Figure axes
    :param csize: dict with chromosome sizes, as {contig_name: size}
    :param segment_colors: color specification for segments. One of [black, difference (default), cluster, or blue_red (any other input)].
    :param sigmas: boolean, True (default) if segments should have heights determined by sigma values
    :param min_seg_lw: Segment line_width (for all segments if sigmas=False or minimum if sigmas=True); default=2
    :param y_upper_lim: yaxis upper limit; default=2
    :return: None (modifies given figure.axes)
    """
    if not min_seg_lw:
        min_seg_lw = 2
    if not y_upper_lim:
        y_upper_lim = 2

    seg_df, chr_order, chrom_start, col_names = prepare_df(seg_df, csize, suffix='.bp')
    add_background(ax, chr_order, csize, height=7)

    # determine segment colors based on input
    if segment_colors == 'difference' or segment_colors is None:
        seg_df['color_bottom'], seg_df['color_top'] = calc_color(seg_df, col_names['mu_major'], col_names['mu_minor'])
    elif segment_colors == 'black':
        seg_df['color_bottom'] = '#000000'
        seg_df['color_top'] = '#000000'
    elif segment_colors == 'cluster':
        phylogic_color_dict = get_phylogic_color_scale()
        seg_df['color_bottom'] = seg_df['cluster_assignment'].map(phylogic_color_dict)
        seg_df['color_top'] = seg_df['color_bottom']
    else:
        seg_df['color_bottom'] = '#2C38A8'  # blue
        seg_df['color_top'] = '#E6393F'  # red

    # draw segments as lines with default line width
    ax.hlines(seg_df[col_names['mu_minor']].values, seg_df['genome_start'], seg_df['genome_end'],
              color=seg_df['color_bottom'], lw=min_seg_lw)
    ax.hlines(seg_df[col_names['mu_major']].values, seg_df['genome_start'], seg_df['genome_end'],
              color=seg_df['color_top'], lw=min_seg_lw)

    # if sigmas are desired, draw over segments
    if sigmas or sigmas is None:
        if col_names['sigma_major'] not in seg_df or col_names['sigma_minor'] not in seg_df:
            print(f'Displaying sigmas is desired, but no sigma columns (i.e. {col_names["sigma_major"]}) exist.')
        else:
            for _, x in seg_df.iterrows():
                ax.add_patch(patches.Rectangle(
                    (x['genome_start'], x[col_names['mu_major']] - x[col_names['sigma_major']]),
                    x['genome_end'] - x['genome_start'], 2 * x[col_names['sigma_major']],
                    color=x['color_top'],
                    alpha=1,
                    linewidth=0
                ))
                ax.add_patch(patches.Rectangle(
                    (x['genome_start'], x[col_names['mu_minor']] - x[col_names['sigma_minor']]),
                    x['genome_end'] - x['genome_start'], 2 * x[col_names['sigma_minor']],
                    color=x['color_bottom'],
                    alpha=1,
                    linewidth=0
                ))

    # layout (can be overridden)
    ax.set_xticks(np.asarray(list(chrom_start.values())[:-1]) + np.asarray(list(csize.values())) / 2)
    ax.tick_params(axis='x', bottom=False)
    ax.set_xticklabels(chr_order, fontsize=10)
    for tick in ax.xaxis.get_major_ticks()[1::2]:
        tick.set_pad(12)
    ax.set_xlim(0, chrom_start['Z'])

    ax.set_yticks(list(range(y_upper_lim + 1)))
    ax.set_yticklabels([str(i) for i in range(y_upper_lim + 1)], fontsize=12)
    ax.set_ylim(-0.05, y_upper_lim + 0.05)
    plt.setp(ax.spines.values(), visible=False)
    ax.spines['left'].set(lw=1, position=('outward', 10), bounds=(0, y_upper_lim), visible=True)
    plt.xlabel("Chromosome")
    plt.ylabel("Allelic Copy Number")


def plot_acr_interactive(seg_df, fig, csize,
                         segment_colors='difference', sigmas=True, min_seg_lw=0.015, y_upper_lim=2, row=0):
    """Create interactive plotly Allelic Copy Ratio plot for given segment profile.

    :param seg_df: pandas.DataFrame with segment profile (allelic CN mu and sigmas)
    :param fig: plotly Figure; must be a subplots Figure (created with plotly.subplots.make_subplots())
    :param csize: dict with chromosome sizes, as {contig_name: size}
    :param segment_colors: color specification for segments. One of [black, difference (default), cluster, or blue_red (any other input)].
    :param sigmas: boolean, True (default) if segments should have heights determined by sigma values
    :param min_seg_lw: Segment line_width (for all segments if sigmas=False or minimum if sigmas=True); default=0.015
    :param y_upper_lim: yaxis upper limit; default=2
    :param row: row in subplots Figure to place plot; default=0
    :return: (trace start num, trace end num) for later modification; additionally modifies given Figure
    """
    # fig should have background set to white
    seg_df, chr_order, chrom_start, col_names = prepare_df(seg_df, csize, suffix='.bp')
    add_background(fig, chr_order, csize, row=row+1)

    seg_df['color_bottom_diff'], seg_df['color_top_diff'] = calc_color(seg_df, col_names['mu_major'], col_names['mu_minor'])
    if 'cluster_assignment' in seg_df.columns:
        phylogic_color_dict = get_phylogic_color_scale()
        seg_df['color_bottom_cluster'] = seg_df['cluster_assignment'].map(phylogic_color_dict)
        seg_df['color_top_cluster'] = seg_df['color_bottom_cluster']

    if segment_colors == 'difference':
        seg_df['color_bottom'], seg_df['color_top'] = seg_df['color_bottom_diff'], seg_df['color_top_diff']
    elif segment_colors == 'cluster' and 'cluster_assignment' in seg_df.columns:
        seg_df['color_bottom'], seg_df['color_top'] = seg_df['color_bottom_cluster'], seg_df['color_top_cluster']
    else:
        seg_df['color_bottom'] = '#2C38A8'  # blue
        seg_df['color_top'] = '#E6393F'  # red

    trace_num = len(fig.data)
    if sigmas and col_names['sigma_major'] not in seg_df:
            print(f'Displaying sigmas is desired, but no sigma columns (i.e. {col_names["sigma_major"]}) exist.')
            sigmas = False
    seg_df.apply(lambda x: make_cnv_scatter(x, fig, col_names, lw=min_seg_lw, row_num=row+1, sigmas=sigmas), axis=1)

    # modify layout
    fig.update_xaxes(showgrid=False,
                     zeroline=False,
                     tickvals=np.asarray(list(chrom_start.values())[:-1]) + np.asarray(list(csize.values())) / 2,
                     ticktext=chr_order,
                     tickfont_size=10,
                     tickangle=0,
                     range=[0, chrom_start['Z']])
    fig.update_xaxes(title_text="Chromosome", row=-1, col=1)
    fig.update_yaxes(showgrid=False,
                     zeroline=False,
                     tickvals=list(range(int(np.floor(y_upper_lim)) + 1)),
                     ticktext=[str(i) for i in range(int(np.floor(y_upper_lim)) + 1)],
                     tickfont_size=12,
                     ticks="outside",
                     range=[-0.05, y_upper_lim + 0.05],
                     title_text="Allelic Copy Number")

    ################
    fig.update_layout(plot_bgcolor='white')  # title=mut_df.iloc[0]['Patient_ID'],

    return trace_num, len(fig.data)


def make_cnv_scatter(series, fig, col_names, lw=0.015, row_num=1, sigmas=False):
    """Add segment to figure as Scatter traces

    :param series: pandas.Series for single segment
    :param fig: plotly.Figure
    :param col_names: dictionary specifying correct column names, as {generic_name: name_in_series}
    :param lw: Segment line_width (for all segments if sigmas=False or minimum if sigmas=True); default=0.015
    :param row_num: specified row (1-index)
    :param sigmas: boolean, True if segments should have heights determined by sigma values; default = False
    :return: None (modifies given Figure)
    """
    start = series['genome_start']
    end = series['genome_end']
    mu_maj = series[col_names['mu_major']]
    mu_min = series[col_names['mu_minor']]
    sigma = series[col_names['sigma_major']] if sigmas else 0
    length = end - start
    n_probes = series['n_probes'] if 'n_probes' in series else np.NaN
    color_maj = series['color_top']
    color_min = series['color_bottom']
    cluster = series['cluster_assignment'] if 'cluster_assignment' in series else np.NaN

    fig.add_trace(go.Scatter(x=[start, start, end, end],
                  y=[mu_min + sigma, mu_min - sigma, mu_min - sigma, mu_min + sigma],
                  fill='toself', fillcolor=color_min, mode='none',
                  hoverinfo='none', name='cnv_sigma',
                  showlegend=False, visible=sigmas), row=row_num, col=1)
    fig.add_trace(go.Scatter(x=[start, start, end, end],
                  y=[mu_maj + sigma, mu_maj - sigma, mu_maj - sigma, mu_maj + sigma],
                  fill='toself', fillcolor=color_maj, mode='none',
                  hoverinfo='none', name='cnv_sigma',
                  showlegend=False, visible=sigmas), row=row_num, col=1)
    fig.add_trace(go.Scatter(x=[start, start, end, end],
                  y=[mu_min + lw, mu_min - lw, mu_min - lw, mu_min + lw],
                  fill='toself', fillcolor=color_min, mode='none',
                  hoveron='fills', name='cnv',
                  text=f'chr{series["Chromosome"]}:{series["Start.bp"]}-{series["End.bp"]}; '
                       f'CN Minor: {mu_min:.2f} +-{sigma:.4f}; '  # todo make original, so no updating needed
                       f'Cluster: {cluster}; '
                       f'Length: {length:.2e} ({n_probes} probes)',
                  showlegend=False), row=row_num, col=1)
    fig.add_trace(go.Scatter(x=[start, start, end, end],
                  y=[mu_maj + lw, mu_maj - lw, mu_maj - lw, mu_maj + lw],
                  fill='toself', fillcolor=color_maj, mode='none',
                  hoveron='fills', name='cnv',
                  text=f'chr{series["Chromosome"]}:{series["Start.bp"]}-{series["End.bp"]}; '
                       f'CN Major: {mu_maj:.2f} +-{sigma:.4f}; '  # todo make original so no updating needed
                       f'Cluster: {cluster}; '
                       f'Length: {length:.2e} ({n_probes} probes)',
                  showlegend=False), row=row_num, col=1)


def update_cnv_scatter_cn(fig, major, minor, sigma, start_trace, end_trace, lw=0.015):
    """Updates y values for CNV traces from start_trace to end_trace given by major/minor lists (optionally change line width also).

    Critical that original traces were added in order: minor (sigma), major (sigma), minor, major as performed in make_cnv_scatter method
    :param fig: plotly.Figure
    :param major: array-like, new major allele mu values
    :param minor: array-like, new minor allele mu values
    :param sigma: array-like, new sigma values
    :param start_trace: which trace to begin with in Figure
    :param end_trace: which trace to end with in Figure
    :param lw: Segment line_width (for all segments if sigmas=False or minimum if sigmas=True); default=0.015
    :return: None
    """
    assert end_trace - start_trace == len(major) * 4 and len(major) == len(minor) == len(sigma)

    for i, (minor_val, major_val, sigma) in enumerate(zip(minor, major, sigma)):
        fig.data[start_trace + 4 * i]['y'] = [minor_val + sigma, minor_val - sigma, minor_val - sigma, minor_val + sigma]
        fig.data[start_trace + 4 * i + 1]['y'] = [major_val + sigma, major_val - sigma, major_val - sigma, major_val + sigma]
        fig.data[start_trace + 4 * i + 2]['y'] = [minor_val + lw, minor_val - lw, minor_val - lw, minor_val + lw]
        fig.data[start_trace + 4 * i + 3]['y'] = [major_val + lw, major_val - lw, major_val - lw, major_val + lw]


def update_cnv_scatter_color(fig, color_minor, color_major, start_trace, end_trace):
    """Updates colors of the segments, based on given arrays and trace numbers.
    
    :param fig: plotly.Figure
    :param color_minor: array-like, new minor allele color values
    :param color_major: array-like, new major allele color values
    :param start_trace: which trace to begin with in Figure
    :param end_trace: which trace to end with in Figure
    :return: None
    """
    assert end_trace - start_trace == len(color_minor) * 4 == len(color_major) * 4

    for i, (minor_val, major_val) in enumerate(zip(color_minor, color_major)):
        fig.data[start_trace + 4 * i]['fillcolor'] = minor_val
        fig.data[start_trace + 4 * i + 1]['fillcolor'] = major_val
        fig.data[start_trace + 4 * i + 2]['fillcolor'] = minor_val
        fig.data[start_trace + 4 * i + 3]['fillcolor'] = major_val


def update_cnv_scatter_sigma_toggle(fig, sigmas):
    """Changes the visibility of the sigmas.
    
    :param fig: plotly.Figure
    :param sigmas: boolean, True if segments should have heights determined by sigma values
    :return: None
    """
    fig.update_traces(dict(visible=sigmas), selector={'name': 'cnv_sigma'})


def add_background(ax, chr_order, csize, height=100, row=1):
    """Add background alternating gray/white bars to demarcate chromosomes.
    
    :param ax: matplotlib axes or plotly.Figure
    :param chr_order: contig names in order as list
    :param csize: dict with chromosome sizes, as {contig_name: size}
    :param height: height of bars, default=100
    :param row: specified row (1-index); only used if plotly Figure given
    :return: None
    """
    base_start = 0
    chrom_ticks = []
    patch_color = 'white'
    for chrom in chr_order:
        if type(ax) == go.Figure:
            ax.add_vrect(base_start, base_start + csize[chrom], fillcolor=patch_color,
                          opacity=0.1, layer='below', line_width=0, exclude_empty_subplots=False, row=row)
        else:
            p = patches.Rectangle((base_start, -0.2), csize[chrom], height, fill=True, facecolor=patch_color,
                                  edgecolor=None, alpha=.1)  # Background
            ax.add_patch(p)
        patch_color = 'gray' if patch_color == 'white' else 'white'
        chrom_ticks.append(base_start + csize[chrom] / 2)
        base_start += csize[chrom]


def calc_color(seg_df, major, minor):
    """Calculate major/minor allele colors based on the difference between them
    
    :param seg_df: pandas.DataFrame with segment data
    :param major: column name for mu_major
    :param minor: column name for mu_minor
    :return: (array of minor allele colors, array of major allele colors)
    """
    from matplotlib import colors
    cmap = colors.LinearSegmentedColormap.from_list("", ["blue", "purple", "red"])
    color_bottom = seg_df.apply(lambda x: colors.rgb2hex(cmap(
        int(np.floor(max(0, (0.5 - 0.5 * scale_diff(x[major] - x[minor])) * 255))))),
                                          axis=1)
    color_top = seg_df.apply(lambda x: colors.rgb2hex(cmap(
        int(np.floor(min(255, (0.5 + 0.5 * scale_diff(x[major] - x[minor])) * 255))))),
                                       axis=1)
    return color_bottom, color_top


def scale_diff(mu_diff):
    """Transforms distance between alleles for use in color formula    
    :param mu_diff: Distance between alleles
    :return: Transformed value
    """
    return (7*mu_diff**2) / (7*mu_diff**2 + 10)


def prepare_df(df, csize, suffix='.bp'):
    """Preparation of dataframe for use (adding genome_position), collecting column names, and chromosome starting positions
    
    :param df: pandas.DataFrame segment profile
    :param csize: dict with chromosome sizes, as {contig_name: size}
    :param suffix: suffix on "Start" and "End" position columns
    :return: (modified_segment_df, chromosome_order_list, chromsome_start_dict, column_names_dict)
    """
    # discover columns
    if 'mu.major' in df.columns:
        col_names = dict(
            mu_major = 'mu.major',
            mu_minor = 'mu.minor',
            sigma_major = 'sigma.major',
            sigma_minor = 'sigma.minor'
        )
    elif 'hscr.a2' in df.columns:
        col_names = dict(
            mu_major = 'hscr.a2',
            mu_minor = 'hscr.a1',
            sigma_major = 'seg_sigma',  # = tau sigma (not allelic sigma), generally slightly lower
            sigma_minor = 'seg_sigma',  # = tau sigma
        )
    # todo add major and minor case (and no sigma?)
    else:
        col_names = None

    chr_order = natsorted(list(csize.keys()))
    chrom_start = {chrom: start for (chrom, start) in
                   zip(np.append(chr_order, 'Z'), np.cumsum([0] + [csize[a] for a in chr_order]))}

    df['Chromosome'] = df['Chromosome'].astype(str)
    df = df[df['Chromosome'].isin(chr_order)]

    df[f'Start{suffix}'] = df[f'Start{suffix}'].astype(int)
    df[f'End{suffix}'] = df[f'End{suffix}'].astype(int)
    df['genome_start'] = df.apply(lambda x: chrom_start[str(x['Chromosome'])] + x[f'Start{suffix}'], axis=1)
    df['genome_end'] = df.apply(lambda x: chrom_start[str(x['Chromosome'])] + x[f'End{suffix}'], axis=1)

    return df, chr_order, chrom_start, col_names


def get_hex_string(c):
    return '#{:02X}{:02X}{:02X}'.format(*c)


def get_phylogic_color_scale():
    """Generate dictionary defining phylogic cluster colors."""
    phylogic_color_list = [[166, 17, 129],
                           [39, 140, 24],
                           [103, 200, 243],
                           [248, 139, 16],
                           [16, 49, 41],
                           [93, 119, 254],
                           [152, 22, 26],
                           [104, 236, 172],
                           [249, 142, 135],
                           [55, 18, 48],
                           [83, 82, 22],
                           [247, 36, 36],
                           [0, 79, 114],
                           [243, 65, 132],
                           [60, 185, 179],
                           [185, 177, 243],
                           [139, 34, 67],
                           [178, 41, 186],
                           [58, 146, 231],
                           [130, 159, 21],
                           [161, 91, 243],
                           [131, 61, 17],
                           [248, 75, 81],
                           [32, 75, 32],
                           [45, 109, 116],
                           [255, 169, 199],
                           [55, 179, 113],
                           [34, 42, 3],
                           [56, 121, 166],
                           [172, 60, 15],
                           [115, 76, 204],
                           [21, 61, 73],
                           [67, 21, 74],  # Additional colors, uglier and bad
                           [123, 88, 112],
                           [87, 106, 46],
                           [37, 66, 58],
                           [132, 79, 62],
                           [71, 58, 32],
                           [59, 104, 114],
                           [46, 107, 90],
                           [84, 68, 73],
                           [90, 97, 124],
                           [121, 66, 76],
                           [104, 93, 48],
                           [49, 67, 82],
                           [71, 95, 65],
                           [127, 85, 44],  # even more additional colors, gray
                           [88, 79, 92],
                           [220, 212, 194],
                           [35, 34, 36],
                           [200, 220, 224],
                           [73, 81, 69],
                           [224, 199, 206],
                           [120, 127, 113],
                           [142, 148, 166],
                           [153, 167, 156],
                           [162, 139, 145],
                           [0, 0, 0]]  # black
    colors_dict = {str(i): get_hex_string(c) for i, c in enumerate(phylogic_color_list)}
    return colors_dict


def save_static_plot(seg_df, output_fn, csize=None,
                     segment_colors=None, sigmas=None, min_seg_lw=None, y_upper_lim=None):
    if not csize:
        # get max positions for each chromosome
        csize = seg_df.groupby('Chromosome')['End.bp'].max().to_dict()

    fig, ax = plt.subplots()
    plot_acr_static(seg_df, ax=ax, csize=csize, segment_colors=segment_colors,
                    sigmas=sigmas, min_seg_lw=min_seg_lw, y_upper_lim=y_upper_lim)

    fig.savefig(output_fn)


def main():
    # parse args
    import argparse
    import os

    parser = argparse.ArgumentParser(description='Save static CN Profile plot for this segment dataframe')
    parser.add_argument("segment_fn", help='CN Segment Profile filename')
    parser.add_argument("output_fn", help='Output path for saved figure')
    parser.add_argument("--csize_file", help='tsv file containing chromosome sizes')
    parser.add_argument("-sc", "--segment_colors", choices=['black', 'difference', 'cluster', 'blue_red'],
                        help='Method for determining segment colors')
    parser.add_argument("--hide_sigmas", dest='sigmas', action='store_false', help='Do not display segment sigmas')
    parser.add_argument("--min_seg_lw",
                        help='Segment line_width (all segments if sigmas are hidden else minimum); default=2')
    parser.add_argument("--y_upper", help='yaxis upper limit; default=2')

    args = parser.parse_args()

    if args.csize_file and os.path.exists(args.csize_file):
        _, ext = os.path.splitext(args.csize_file)
        if ext == '.bed':
            columns = ['chr', 'start', 'len']  # three columns if bed file
        else:
            columns = ['chr', 'len']
        csize = pd.read_csv(args.csize_file, sep='\t', header=None, names=columns).set_index(
            'chr', inplace=True).to_dict()['len']
    else:
        csize = None

    segment_df = pd.read_csv(args.segment_fn, sep='\t', header=0)

    save_static_plot(segment_df, args.output_fn, csize=csize, segment_colors=args.segment_colors,
                     sigmas=args.sigmas, min_seg_lw=args.min_seg_lw, y_upper_lim=args.y_upper)


if __name__ == '__main__':
    main()
