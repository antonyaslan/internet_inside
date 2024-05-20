mod control_system;

use pyo3::prelude::*;
use crate::control_system::controller::PID;
use crate::control_system::process::WaterTank;

#[pyfunction]
fn control_it(pid: &mut PID, set_point: f64, measured_value: f64) -> PyResult<()> {
    Ok(pid.control(set_point, measured_value))
}

#[pyfunction]
fn get_control_signal(pid: &PID) -> PyResult<f64> {
    Ok(pid.get_control_signal())
}

#[pyfunction]
fn update_process(water_tank: &mut WaterTank, flow_rate: f32) -> PyResult<()> {
    Ok(water_tank.update_process(flow_rate))
}

#[pyfunction]
fn get_water_height(water_tank: &WaterTank) -> PyResult<f32> {
    Ok(water_tank.get_water_height())
}

#[pyfunction]
fn get_water_volume(water_tank: &WaterTank) -> PyResult<f32> {
    Ok(water_tank.get_water_volume())
}

#[pymodule]
fn pyg_control_system(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PID>()?;
    m.add_function(wrap_pyfunction!(control_it, m)?)?;
    m.add_function(wrap_pyfunction!(get_control_signal, m)?)?;
    m.add_class::<WaterTank>()?;
    m.add_function(wrap_pyfunction!(update_process, m)?)?;
    m.add_function(wrap_pyfunction!(get_water_height, m)?)?;
    m.add_function(wrap_pyfunction!(get_water_volume, m)?)?;
    Ok(())
}

