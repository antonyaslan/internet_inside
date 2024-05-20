/**
 * PID controller code based on Java implementation from:
 * "Computer Control: An Overview - Educational Version 2021"
 * written by: Björn Wittenmark, Karl Johan Åström, Karl-Erik Årzén
 * 
 * Customized for the water tank process, detailed in process.rs
 */

use pyo3::prelude::*;

struct Signals {
    uc: f64,        // Input: set point
    y: f64,         // Input: Measured variable
    v: f64,         // Output: Controller output
    u: f64          // Output: Limited controller output
}

struct States {
    i: f64,         // I-part
    d: f64,         // D-part
    y_old: f64       // Delayed measured variable
}

struct Parameters {
    k: f64,         // Proportional gain
    t_i: f64,       // Integral time
    t_d: f64,       // Derivative time
    t_t: f64,       // Reset time
    n: f64,         // Max derivative gain
    b: f64,         // Fraction of set point in proportional term
    // [m^2 / s], volumetric flow rates
    u_low: f64,     // Low output limit
    u_high: f64,    // High output limit
    h: f64,         // Sampling period, needs to match mobile unit's h
    bi: f64,        // Helper coefficient
    ar: f64,        // Helper coefficient
    bd: f64,        // Helper coefficient
    ad: f64         // Helper coefficient
}
#[pyclass]
pub struct PID {
    signals: Signals,
    states: States,
    params: Parameters
}

#[pymethods]
impl PID {
    #[new]
    fn new() -> PID {
        let mut pid: PID = PID {
            signals: Signals {
                uc: 0.0,
                y: 0.0,
                v: 0.0,
                u: 0.0
            },
            states: States {
                i: 0.0,
                d: 0.0,
                y_old: 0.0
            },
            params: Parameters {
                k: 4.4,
                t_i: 0.4,
                t_d: 0.2,
                t_t: 10.0,
                n: 10.0,
                b: 1.0,
                u_low: 8.86e-6,
                u_high: 1.98e-5,
                h: 5.0,
                // Set following to 0 when instantiating, change later
                bi: 0.0,
                ar: 0.0,
                bd: 0.0,
                ad: 0.0
            }
        };
        // Set helper coefficients
        pid.params.bi = pid.params.k*pid.params.h / pid.params.t_i;
        pid.params.ar = pid.params.h / pid.params.t_t;
        pid.params.ad = pid.params.t_d/(pid.params.t_d + pid.params.n*pid.params.h);
        pid.params.bd = pid.params.k*pid.params.n*pid.params.ad;
        pid
    }

    /**
    Calculate PID controller output
    */
    fn calculate_output(&mut self, uc:f64, y:f64) -> f64 {
        // Update internal signals
        self.signals.uc = uc;
        self.signals.y = y;
        // Calculate proportional part
        let p: f64 = self.params.k*(self.params.b*uc - y);
        // Calculate new derivative part
        self.states.d = self.params.ad*self.states.d - 
            self.params.bd*(y - self.states.y_old);
        // Calculate raw control signal output
        self.signals.v = p + self.states.i + self.states.d;
        // Clamp to desired output range
        if self.signals.v < self.params.u_low {
            self.signals.u = self.params.u_low;
        } else {
            if self.signals.v > self.params.u_high {
                self.signals.u = self.params.u_high;
            } else {
                self.signals.u = self.signals.v;
            }
        }
        self.signals.u
    }

    /**
    Update I-part and update y_old signal
    */
    fn update_state(&mut self, u:f64) -> () {
        self.states.i = self.states.i + 
            self.params.bi*(self.signals.uc - self.signals.y) +
            self.params.ar*(u - self.signals.v);
        self.states.y_old = self.signals.y;
    }

    /**
     * Run one control iteration. Takes in set point and measured value,
     * and returns control signal
     * Updates internal signals
     */
    pub fn control(&mut self, uc: f64, y: f64) -> () {
        let u: f64 = self.calculate_output(uc, y);
        self.update_state(u);
    }

    pub fn get_control_signal(&self) -> f64 {
        self.signals.u
    }

}