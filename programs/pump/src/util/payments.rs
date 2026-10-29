use anchor_lang::prelude::*;
use crate::create_v2::{CreateV2,mayhem_interface};use crate::*;use crate::trade_types::{BondingCurve,TradeEvent,Shareholder};use crate::pump_fees::accounts::SharingConfig;

#[inline(never)]pub fn initialize_mayhem<'info>(ctx:&Context<'_, '_, '_, 'info, CreateV2<'info>>)->Result<()>{
 let a=&ctx.accounts;
 mayhem_interface::cpi::initialize_mayhem_state(CpiContext::new_with_signer(
  a.mayhem_program_id.to_account_info(),mayhem_interface::cpi::accounts::InitializeMayhemState{
   payer:a.user.to_account_info(),
   mint_authority:a.mint_authority.to_account_info(),
   sol_vault:a.sol_vault.to_account_info(),
   mint:a.mint.to_account_info(),
   token_vault:a.mayhem_token_vault.to_account_info(),
   global_params:a.global_params.to_account_info(),
   mayhem_state:a.mayhem_state.to_account_info(),
   system_program:a.system_program.to_account_info(),
   token_program:a.token_program.to_account_info(),
   associated_token_program:a.associated_token_program.to_account_info(),
  },&[&[b"mint-authority",&[ctx.bumps.mint_authority]]],
 ))
}
impl AnchorDeserialize for OptionBool {
 fn deserialize_reader<R:std::io::Read>(reader:&mut R)->std::io::Result<Self>{
  let mut b=[0u8];match reader.read_exact(&mut b){Err(e) if e.kind()==std::io::ErrorKind::UnexpectedEof=>Ok(Self(false)),Err(e)=>Err(e),Ok(())=>match b[0]{0=>Ok(Self(false)),1=>Ok(Self(true)),value=>Err(std::io::Error::new(std::io::ErrorKind::InvalidData,format!("Invalid bool representation: {}",value)))}}
 }
}
/// Shareholders of an optional fee-sharing config; empty or undecodable data reads as none.
#[inline(never)]
pub fn sharing_config_shareholders(account:&AccountInfo)->Result<Option<Vec<Shareholder>>>{
 if account.data_is_empty(){return Ok(None);}
 let data=account.try_borrow_data()?;
 match SharingConfig::try_deserialize(&mut &data[..]){Ok(config)=>Ok(Some(config.shareholders)),Err(_)=>Ok(None)}
}
pub fn trade_event(curve:&BondingCurve,global:&Global,volume:&crate::UserVolumeAccumulator,user:&Pubkey,mint:&Pubkey,is_buy:bool,token_amount:u64,quote_amount:u64,fees:&crate::trade::TradeFees,buyback_fee:u64,unparsed_trailing_field:u64,ix_name:&str,timestamp:i64)->TradeEvent{
    let virtual_quote_reserves=curve.virtual_quote_reserves;let real_quote_reserves=curve.real_quote_reserves;
    let quote_mint=curve.quote_mint;let is_sol=quote_mint==Pubkey::default();
    TradeEvent{
        quote_mint:curve.quote_mint,
        mint:*mint,
        sol_amount:if is_sol{quote_amount}else{0},
        is_buy,
        token_amount,
        user:*user,
        timestamp,
        virtual_sol_reserves:if is_sol{virtual_quote_reserves}else{0},
        virtual_token_reserves:curve.virtual_token_reserves,
        real_token_reserves:curve.real_token_reserves,
        fee_recipient:Pubkey::default(),
        fee_basis_points:fees.protocol_fee_bps,
        fee:fees.protocol_fee,
        creator:curve.creator,
        creator_fee_basis_points:fees.creator_fee_bps,
        creator_fee:fees.creator_fee,
        track_volume:false,
        total_unclaimed_tokens:volume.total_unclaimed_tokens,
        total_claimed_tokens:volume.total_claimed_tokens,
        current_sol_volume:volume.current_sol_volume,
        last_update_timestamp:volume.last_update_timestamp,
        ix_name:ix_name.to_string(),
        mayhem_mode:curve.is_mayhem_mode,
        cashback_fee_basis_points:0,
        cashback:0,
        real_sol_reserves:if is_sol{real_quote_reserves}else{0},
        buyback_fee_basis_points:if curve.is_mayhem_mode{0}else{global.buyback_basis_points},
        buyback_fee,
        shareholders:vec![],
        quote_amount,
        virtual_quote_reserves,
        real_quote_reserves,
        holder_rewards_bps:if curve.is_holder_reward{fees.creator_fee_bps}else{0},
        holder_rewards:if curve.is_holder_reward{fees.creator_fee}else{0},
        creator_fee_unclaimed:curve.creator_fee,
        unparsed_trailing_field,
    }
}
