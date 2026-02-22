import marimo

__generated_with = "0.19.9"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    from core.datasources import query
    import numpy as np
    import plotly.graph_objects as go
    import polars as pl
    import pandas as pd
    from scipy.optimize import minimize
    from sklearn.neighbors import KernelDensity
    import matplotlib as mlt
    from pypfopt import efficient_frontier 
    from pypfopt import risk_models
    from pypfopt import expected_returns

    return KernelDensity, go, minimize, mo, np, pd, pl, query


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Marcenko-Pastur Distribution

    This states that if we consider a matrix of independent and identically distributed random observations $X$, of size $T \times N$ (in finance, $T$ is time and $N$ is, say, each stock), where the underlying process generating the observations has zero mean and variance $\sigma^2$, then

    the matrix
    \[
    C = \frac{1}{T} X^\top X
    \]
    has eigenvalues $\lambda$ that asymptotically converge (as $N \to \infty$ and $T \to \infty$ with $1 < \frac{T}{N} < +\infty$) to the Marcenko-Pastur probability density function (PDF):

    \[
    f(\lambda) =
    \begin{cases}
    \dfrac{\sqrt{(\lambda_+ - \lambda)(\lambda - \lambda_-)}}{2 \pi q \sigma^2 \lambda}, & \text{for } \lambda \in [\lambda_-, \lambda_+] \\
    0, & \text{otherwise}
    \end{cases}
    \]

    where

    \[
    \lambda_\pm = \sigma^2 (1 \pm \sqrt{q})^2, \quad q = \frac{N}{T}.
    \]

    When $\sigma^2 = 1$, then $C$ is the correlation matrix associated with $X$.
    """)
    return


@app.cell(hide_code=True)
def _(go, np):
    def _func():# Parameters
        N = 500       
        T = 1000      
        q = N / T     

        lambda_minus = (1 - np.sqrt(q))**2
        lambda_plus = (1 + np.sqrt(q))**2
        lambda_vals = np.linspace(lambda_minus, lambda_plus, 1000)

        def marcenko_pastur_pdf(lamb, q):
            pdf = np.sqrt((lambda_plus - lamb) * (lamb - lambda_minus)) / (2 * np.pi * q * lamb)
            return pdf

        pdf_vals = marcenko_pastur_pdf(lambda_vals, q)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=lambda_vals, y=pdf_vals, mode='lines', name='Marcenko-Pastur PDF'))
        fig.update_layout(
            title="Marčenko-Pastur Distribution",
            xaxis_title="Eigenvalue λ",
            yaxis_title="Density",
            template="plotly_white"
        )
        fig.show()
    _func()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Correlation Matrix Computation

    Here the first thing that we have to do is compute the covariance matrix, and then correlation matrix however it is not going to be straight forward. _I don't think that stocks that are IPOS post 2023 are worthy of putting into here as we need enough history._

    So keeping that in mind
    """)
    return


@app.cell
def _(query):
    daily_returns = query("""
    WITH d1 AS (
        SELECT ticker, min(timestamp) AS min_ticker_timestamp FROM ohlcv.ohlcv_1d
        GROUP BY ticker
        HAVING min_ticker_timestamp <= (SELECT min(timestamp) FROM ohlcv.ohlcv_1d)
    ),

    d2 AS (
        SELECT 
                timestamp,
                ticker,
                close,
                close - lag(close, 1) OVER (PARTITION BY ticker ORDER BY timestamp) AS daily_returns
            FROM ohlcv.ohlcv_1d 
        WHERE ticker IN (SELECT DISTINCT ticker FROM d1)
        ORDER BY ticker, timestamp
    )

    SELECT * FROM d2 WHERE daily_returns IS NOT NULL
    """)

    daily_returns
    return (daily_returns,)


@app.cell
def _(daily_returns, np, pl):
    returns_wide = daily_returns.pivot(
        values="daily_returns",
        index="timestamp",
        on="ticker",
    )

    returns_clean_np = (
        returns_wide
        .fill_null(0.0)
        .select(pl.all().exclude("timestamp"))
        .to_numpy()
    )

    cov_matrix = np.cov(returns_clean_np, rowvar=False)

    cov_df = pl.DataFrame(
        cov_matrix, 
        schema=[(col, pl.Float64) for col in returns_wide.columns if col != "timestamp"]
    )

    def cov2corr(cov):
        std = np.sqrt(np.diag(cov))
        corr = cov/np.outer(std, std)
        corr[corr<-1], corr[corr>1] = -1, 1
        return corr

    cor_matrix = cov2corr(cov_matrix)

    pl.DataFrame(
            cov2corr(cov_matrix),
            schema=[(col, pl.Float64) for col in returns_wide.columns if col != "timestamp"]
    )
    return cor_matrix, cov2corr, returns_wide


@app.cell
def _(KernelDensity, minimize, np, pd):
    def mpPDF(var, q, points):
        """
        Compute the Marčenko-Pastur probability density function (PDF).

        Parameters:
        var : float
            Variance of the distribution.
        q : float
            Ratio T/N where T is the number of observations and N is the number of variables.
        points : int
            Number of points for the PDF.

        Returns:
        pd.Series
            Marčenko-Pastur PDF values indexed by eigenvalue.
        """
        e_min = var * (1 - (1 / q) ** 0.5) ** 2
        e_max = var * (1 + (1 / q) ** 0.5) ** 2

        eigenvalues = np.linspace(e_min, e_max, points)
        pdf_values = (q / (2 * np.pi * var * eigenvalues)) * np.sqrt((e_max - eigenvalues) * (eigenvalues - e_min))

        pdf_series = pd.Series(pdf_values, index=eigenvalues)
        return pdf_series

    def getPCA(matrix):
        """
        Compute the Principal Components (eigenvalues and eigenvectors) of a symmetric matrix.

        Parameters:
        matrix : np.ndarray
            A symmetric matrix, e.g., a covariance matrix.

        Returns:
        eigenvalues : np.ndarray
            Sorted eigenvalues in descending order (as a 1D array).
        eigenvectors : np.ndarray
            Corresponding eigenvectors as columns, sorted by eigenvalue magnitude.
        """
        eigenvalues, eigenvectors = np.linalg.eigh(matrix)

        sorted_indices = eigenvalues.argsort()[::-1]
        eigenvalues = eigenvalues[sorted_indices]
        eigenvectors = eigenvectors[:, sorted_indices]

        return eigenvalues, eigenvectors

    def fitKDE(observations, bandwidth=0.25, kernel='gaussian', x=None):
        """
        Fit a Kernel Density Estimator (KDE) and return the estimated PDF as a pandas Series.

        Parameters:
        observations : np.ndarray
            1D or 2D array of data points to fit KDE.
        bandwidth : float, optional
            Smoothing parameter for KDE. Default is 0.25.
        kernel : str, optional
            Kernel type for KDE (e.g., 'gaussian', 'tophat', 'epanechnikov'). Default is 'gaussian'.
        x : np.ndarray, optional
            Points at which to evaluate the PDF. If None, uses unique observations.

        Returns:
        pd.Series
            Estimated PDF values indexed by x.
        """
        if observations.ndim == 1:
            observations = observations.reshape(-1, 1)

        kde = KernelDensity(kernel=kernel, bandwidth=bandwidth)
        kde.fit(observations)

        if x is None:
            x = np.unique(observations).reshape(-1, 1)

        if x.ndim == 1:
            x = x.reshape(-1, 1)

        log_density = kde.score_samples(x)
        pdf_values = np.exp(log_density)

        pdf_series = pd.Series(pdf_values, index=x.flatten())

        return pdf_series

    def errPDFs(variance, eigenvalues, q, bandwidth, points=1000):
        """
        Compute the Sum of Squared Errors (SSE) between
        theoretical Marčenko-Pastur PDF and empirical KDE PDF.

        Parameters:
        variance : float
            Variance used in the Marčenko-Pastur distribution.
        eigenvalues : np.ndarray
            Observed eigenvalues from data.
        q : float
            T/N ratio.
        bandwidth : float
            KDE bandwidth parameter.
        points : int, optional
            Number of points for evaluating the theoretical PDF.

        Returns:
        float
            Sum of squared errors between empirical and theoretical PDFs.
        """

        theoretical_pdf = mpPDF(variance, q, points)

        empirical_pdf = fitKDE(
            observations=eigenvalues,
            bandwidth=bandwidth,
            x=theoretical_pdf.index.values
        )
        sse = np.sum((empirical_pdf - theoretical_pdf) ** 2)
        return sse


    def findMaxEval(eigenvalues, q, bandwidth):
        """
        Estimate the optimal variance parameter by minimizing
        the error between empirical and theoretical PDFs.

        Parameters:
        eigenvalues : np.ndarray
            Observed eigenvalues.
        q : float
            T/N ratio.
        bandwidth : float
            KDE bandwidth parameter.

        Returns:
        e_max : float
            Maximum theoretical eigenvalue.
        variance : float
            Optimized variance parameter.
        """

        def objective(variance):
            return errPDFs(variance[0], eigenvalues, q, bandwidth)

        result = minimize(
            objective,
            x0=[0.5],  
            bounds=[(1e-5, 1 - 1e-5)]
        )

        if result.success:
            variance = result.x[0]
        else:
            variance = 1.0

        e_max = variance * (1 + np.sqrt(1 / q)) ** 2
        return e_max, variance


    return findMaxEval, fitKDE, getPCA, mpPDF


@app.cell
def _(cor_matrix, findMaxEval, fitKDE, getPCA, go, mpPDF, returns_wide):
    def compare_marcenko(cor_matrix):
        T = returns_wide.shape[0]
        N = returns_wide.shape[1]
        q = T / N
        print("T is ", T, " : N is ", N)
    
        eigenvalues, _ = getPCA(cor_matrix)
    
        bandwidth = 0.01
        eMax, var = findMaxEval(eigenvalues, q, bandwidth)
    
        mp_pdf = mpPDF(var, q, 1000)
        kde_pdf = fitKDE(eigenvalues, bandwidth=bandwidth, x=mp_pdf.index.values)
        # Check the top 5 eigenvalues
        print("Top 5 Eigenvalues:", eigenvalues[:5])
        print("Signal Threshold (eMax):", eMax)
    
        fig = go.Figure()
    
        fig.add_trace(go.Scatter(
            x=mp_pdf.index,
            y=mp_pdf.values,
            mode='lines',
            name='Marcenko-Pastur PDF'
        ))
    
        fig.add_trace(go.Scatter(
            x=kde_pdf.index,
            y=kde_pdf.values,
            mode='lines',
            name='Empirical KDE'
        ))
    
        fig.add_vline(x=eMax)
    
        fig.update_layout(
            title='Marcenko-Pastur Fit vs Empirical Eigenvalue Distribution',
            xaxis_title='Eigenvalue',
            yaxis_title='Density'
        )
    
        fig.show()

    compare_marcenko(cor_matrix)
    return


@app.cell
def _(mpPDF):
    test_pdf = mpPDF(var=1.0, q=10.0, points=1000)
    test_pdf.plot()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The reason that the above stuffs are not looking really good is because I think there is a large eigen value that eats all the 'tones' because one of the signals is the market component itself.

    So we can consider to remove that using **Detoning**.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Denoising and Detoning
    """)
    return


@app.cell
def _(cor_matrix, cov2corr, findMaxEval, fitKDE, getPCA, go, np, returns_wide):
    def denoisedCorr(eigenvalues, eigenvectors, n_facts):
        """
        Denoise correlation matrix using eigenvalue clipping.

        Parameters:
        eigenvalues : np.ndarray (1D)
            Sorted eigenvalues (descending).
        eigenvectors : np.ndarray
            Corresponding eigenvectors.
        n_facts : int
            Number of signal eigenvalues to preserve.

        Returns:
        np.ndarray
            Denoised correlation matrix.
        """

        eigenvalues = np.array(eigenvalues).copy()

        noise_average = eigenvalues[n_facts:].mean()
        eigenvalues[n_facts:] = noise_average
        Lambda = np.diag(eigenvalues)
        corr_denoised = eigenvectors @ Lambda @ eigenvectors.T
        corr_denoised = cov2corr(corr_denoised)

        return corr_denoised

    def plot_before_and_after(raw_corr, clean_corr):
        evals_raw, _ = getPCA(raw_corr)
        evals_clean, _ = getPCA(clean_corr)
    
        kde_raw = fitKDE(evals_raw, bandwidth=0.01)
        kde_clean = fitKDE(evals_clean, bandwidth=0.01)
    
        fig = go.Figure()
    
        fig.add_trace(go.Scatter(
            x=kde_raw.index, y=kde_raw.values,
            mode='lines', name='Before'
        ))
    
        fig.add_trace(go.Scatter(
            x=kde_clean.index, y=kde_clean.values,
            mode='lines', name='After'
        ))
    
        fig.update_layout(
            title='Eigenvalue Distribution: Before vs After',
            xaxis_title='Eigenvalue',
            yaxis_title='Density',
            xaxis_range=[0, 5] 
        )
    
        fig.show()

    def detonedCorr(denoised_corr, n_facts=1):
        evals, evecs = getPCA(denoised_corr)
        evals_detoned = evals.copy()
        evals_detoned[:n_facts] = 0 
        corr_detoned_raw = evecs @ np.diag(evals_detoned) @ evecs.T
        corr_detoned = cov2corr(corr_detoned_raw)
        return corr_detoned
    
    def _func_fixed():
        T = returns_wide.shape[0]
        N = returns_wide.shape[1]
        q = T / N
        eigenvalues, eigenvectors = getPCA(cor_matrix)
        eMax, var = findMaxEval(eigenvalues, q, bandwidth=0.01)
        n_facts = len(eigenvalues[eigenvalues > eMax])
        print("Signals preserved:", n_facts)
        denoised_corr_matrix = denoisedCorr(eigenvalues, eigenvectors, n_facts)
        plot_before_and_after(cor_matrix, denoised_corr_matrix)

        detoned_corr_matrix = detonedCorr(denoised_corr_matrix)
        plot_before_and_after(denoised_corr_matrix, detoned_corr_matrix)
        return denoised_corr_matrix

    denoised_corr_matrix = _func_fixed()
    return (denoised_corr_matrix,)


@app.cell
def _(denoised_corr_matrix, minimize, np, pl, returns_wide):
    # returns_wide = daily_returns.pivot(
    #     values="daily_returns",
    #     index="timestamp",
    #     on="ticker",
    # )

    def corr_to_cov(corr, std_dev):
        std_matrix = np.outer(std_dev, std_dev)
        return corr * std_matrix

    def optPort(cov):
        """
        Compute global minimum variance portfolio weights.
        Returns weights that are all non-negative and sum to 1.
        Keeps same API: optPort(cov) -> np.ndarray of weights
        """
        N = cov.shape[0]
        cov_safe = cov + np.eye(N) * 1e-8
        def portfolio_var(w):
            return w.T @ cov_safe @ w
        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1})
        bounds = [(0, 1) for _ in range(N)]
        w0 = np.ones(N) / N
        result = minimize(portfolio_var, w0, method='SLSQP', bounds=bounds, constraints=constraints)
    
        if not result.success:
            return np.ones(N) / N
    
        return result.x

    def _func():
        tickers = [col for col in returns_wide.columns if col != "timestamp"]
        data_matrix = returns_wide.drop("timestamp").select(tickers).fill_null(0).fill_nan(0).to_numpy()
    
        T, N = data_matrix.shape
        q = T / N
        print("q is ", q)
    
        std_dev = data_matrix.std(axis=0)
        cov_matrix = corr_to_cov(denoised_corr_matrix, std_dev)
    
        weights = optPort(cov_matrix)
    
        return pl.DataFrame([dict(zip(tickers, weights))]).unpivot(value_name='weight', variable_name='ticker').sort('weight', descending=True)

    _func()

    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
