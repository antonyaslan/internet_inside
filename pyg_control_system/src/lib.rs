mod controller;

use pyo3::prelude::*;
use crate::controller::PID;

#[pyfunction]
fn control_it(pid: &mut PID, set_point: f64, measured_value: f64) -> PyResult<f64> {
    Ok(pid.control(set_point, measured_value))
}

#[pymodule]
fn pyg_control_system(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PID>()?;
    m.add_function(wrap_pyfunction!(control_it, m)?)?;
    Ok(())
}

