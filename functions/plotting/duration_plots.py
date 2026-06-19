import numpy as np
import matplotlib.pyplot as plt

from functions.plotting.helpers import save_plot

def plot_bars(
    values: np.ndarray,
    colors: np.ndarray|str = 'lightblue',
    labels: list[str]|str = '',
    save_fig: bool=False,
    fig_data: tuple[str, str, str, int]|None=None
):
    indices = [n+1 for n in range(len(values))]

    fig, ax = plt.subplots()

    b = ax.bar(
        x=indices,
        height=values,
        width=1,
        bottom=0,
        align='center',
        color=colors,
        edgecolor='gray',
        linewidth=0.1
    )

    ax.set_title(f"Ordered duration of subcycles")
    ax.set_xlabel('Index')
    ax.set_ylabel('Duration (norm. units)')
    ax.margins(x=0, y=0)

    plt.tight_layout()
    plt.show()

    if fig_data is not None and save_fig:
        save_plot(fig, fig_data)