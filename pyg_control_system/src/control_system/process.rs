/**
 * Water tank process model
 * Based on model in: https://www.inase.org/library/2014/santorini/bypaper/ROBCIRC/ROBCIRC-11.pdf
 */


use std::f32::consts::PI;
use pyo3::prelude::*;

// [m]
const R1: f32 = 0.087;
const R2: f32 = 0.057;

// [m^2 / s]
// K assumes valve height h_v=0.076m
const K: f32 = 3.22e-5;

#[pyclass]
pub struct WaterTank {
    height: f32,
    ext_radius: f32,
    int_radius: f32,
    f: f32,
    k: f32
}

#[pymethods]
impl WaterTank {
    #[new]
    fn new() -> WaterTank {
        let mut water_tank = WaterTank {
            height: 0.0,
            ext_radius: R1,
            int_radius: R2,
            f: 0.0,
            k: K
        };
        water_tank.f = water_tank.ext_radius.powi(2)*PI + water_tank.int_radius.powi(2)*PI;
        water_tank
    }

    pub fn update_process(&mut self, q_in: f32) -> () {
        let dh: f32 = (q_in-self.k*self.height.sqrt()) / self.f;
        self.height = self.height + dh; 
    }

    pub fn get_water_height(&self) -> f32 {
        self.height
    }

    pub fn get_water_volume(&self) -> f32 {
        self.height*self.f
    }
}
