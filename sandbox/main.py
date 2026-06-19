from cycles.cycle_division_functions import compute_level

if __name__ == "__main__":
    # Compute levels
    # manvantara = 64800
    bases = [4, 2]

    # nrows = 3
    # ncols = 3
    # num_levels = nrows * ncols
    num_levels = 3
    levels = [compute_level(depth, bases) for depth in range(1, num_levels+1)]
    # levels = [compute_level(depth, bases, manvantara) for depth in range(1, num_levels + 1)]

    # Uniqueness of colors
    # print([len(np.unique(level[3], axis=0)) == len(level[3]) for level in levels])
    # print([all([len(x[1]) == 1 for x in find_identical(level[3], 10)]) for level in levels])

    # Plot level bars
    # plot_level_bars(levels)

    # Plot quality grid
    # plot_quality_grid(levels, bases[1], nrows, ncols)

    # Plot color graphs
    # level = compute_level(6, bases)
    # plot_cmyk_graph(level)
    # plot_rgb_graph(level)
    # plot_hsv_graph(level)
    # plot_hls_graph(level)
    # plot_overlay(level, bases[1])
    # plot_rgb_scatter_3d(level)
    # plot_rgb_scatter_3d(level, 1, bases[0])
    # plot_quality_scatter_3d(level)
    # plot_circle_diagram(levels, bases[0])

    # fig, ax = plt.subplots()
    # plot_purity_and_dharma(ax, level, bases[1])
    # plt.tight_layout()
    # plt.show()
    # fig.savefig("purity_dharma_v01.png", dpi=600)

    # part_level = partition_level(level, 2, bases[0])
    # plot_quality_grid(part_level, bases[1])

    # extra_depth = 6
    # parent_coords = [[0], [1], [2], [3]]
    # subcycles = [compute_deeper_subcycles(coords, extra_depth, bases) for coords in parent_coords]
    # side = int(np.sqrt(len(parent_coords)))
    # fig, axs = plt.subplots(
    #     ncols=side,
    #     nrows=side,
    #     sharex=True,
    #     sharey=True,
    #     subplot_kw=dict(aspect=1),
    #     gridspec_kw=dict(hspace=0, wspace=0)
    # )
    # for i in range(side):
    #     for j in range(side):
    #         plot_purity_and_dharma(axs[i, j], subcycles[j * side + i])
    # plt.show()


    # lcoords, durations, starts, colors = level
    # hsv = np.array([csys.rgb_to_hsv(*rgb) for rgb in colors])
    # xx = find_identical(hsv[:, 0] * (1.0 - hsv[:, 1]), 10)
    # xx = find_identical(colors[:, 2], 10)
    # xxx = np.array([[x[0], np.sum(durations[x[1]])] for x in xx])
    # fig, ax = plt.subplots()
    # ax.plot(xxx[:,0], xxx[:,1])
    # plt.show()

    # Subcycle comparison graphs
    # selectors = [([], levels[0])] + [([i], levels[1]) for i in range(4)]
    # subcycles = [select_subcycle(*sel) for sel in selectors]
    # plot_comparison_graph(subcycles)

    # Identical durations
    # xx = find_identical_durations(levels[2][1], 10)
    # for x in xx:
    #     print(x)

    # print(int_to_lcoords(41, 4, 3))
    # yy = indentical_duration_lcoords([0,3,1])
    # for y in yy:
    #     print(y, lcoords_to_int(list(y)), compute_duration(list(y)))

    # Relation between identical duration subcycles
    # fig, axs = plt.subplots(1, 2, figsize=(25, 50))
    # for i, ax in enumerate(axs, start=1):
    #     plot_identical_graph(ax, levels[i], find_identical_durations(levels[i][1], 10), ref_level=levels[0], one_to_many=True, show_labels=False)
    # plt.tight_layout()
    # plt.show()

    # Sound waves: Fourier
    # lcoords, durations, starts, rgb, cmyk = compute_level(3, bases, total_duration=60)
    # for c, l, d in zip(cmyk, lcoords, durations):
    #     signal = cmyk_to_fractal_tone(c, l, f0=110, duration=d)
    #     sd.play(signal, samplerate=44100)
    #     sd.wait()

    # Sound wave: multi-level wavelet
    # num_levels = 3
    # levels = [compute_level(depth, bases) for depth in range(1, num_levels+1)]
    # signal = multilevel_fractal_wavelet_synthesis(levels, 60)
    # sd.play(signal, samplerate=44100)
    # sd.wait()

    # Sound wave: single-level wavelet
    # level = compute_level(4, bases)
    # total_duration = 32.0
    # srate = 44100
    # signal, t_axis = fractal_wavelet_synthesis_v02(level, T=total_duration, srate=srate, beta=1.0/(2.0*np.sqrt(2*np.log(2))))
    # sd.play(signal, samplerate=srate)
    # sd.wait()
    # scalogram, freqs = compute_scalogram(signal, srate, num_scales=256, f_min=30.0, f_max=srate/2)
    # plot_scalogram(scalogram, freqs, srate, total_duration)

    """
    # Checks
    depth = 3
    bases = [4, 4]
    total_duration = 64800
    indices = [x for x in range(4**depth)]
    lcoords = [int_to_lcoords(index, bases[1], depth) for index in indices]
    fracs = [lcoords_to_fractional(coord, bases[0]) for coord in lcoords]
    ivectors = [[indicator_vector(i, coord) for i in range(1, 4)] for coord in lcoords]
    rgb = [lcoords_to_rgb(coord, bases[1]) for coord in lcoords]
    sfactor =  (bases[1] - 1) / (1 - bases[1]**(-depth))
    colours = [lcoords_to_colour(coord, sfactor, bases[1]) for coord in lcoords]
    rgb_check = [c[0] + 2 * c[1] + 3 * c[2] for c in rgb]
    tag_check = [fractional_to_lcoords(x, bases[1]) for x in rgb_check]
    durations = [compute_duration(lcoord, total_duration) for lcoord in lcoords]
    dur_check = np.sum(durations)
    starts = [compute_start(lcoord, total_duration) for lcoord in lcoords]
    end_check = starts[-1] + durations[-1]

    print(offsets)
    print([proportions[lcoords[1][:k]] for k in range(len(lcoords[1]))])
    print(dur_check)
    print(end_check)
    for i in range(len(indices)):
        print(indices[i],
              lcoords[i],
              fracs[i],
              ivectors[i],
              rgb[i],
              colours[i],
              rgb_check[i],
              tag_check[i],
              durations[i],
              starts[i])
    """