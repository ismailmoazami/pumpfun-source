use anchor_lang::prelude::*;

pub use crate::payments::migratenp_transfer_native as transfer_native;
// layout-pad
// layout-pad
// layout-pad
// layout-pad
// layout-pad
// layout-pad
// layout-pad
// layout-pad
// layout-pad
// layout-pad
// layout-pad

pub(crate) fn boost_enabled(config: &AccountInfo) -> bool {
    let Ok(data) = config.try_borrow_data() else { return false };
    let mut buf: &[u8] = &data;
    crate::pump_amm::accounts::GlobalConfig::try_deserialize(&mut buf).map_or(false, |global_config| global_config.boost_enabled)
}
