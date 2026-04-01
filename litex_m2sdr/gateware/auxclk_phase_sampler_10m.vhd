library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.gencores_pkg.all;

entity auxclk_phase_sampler_10m is
  port (
    ---------------------------------------------------------------------------
    -- Clocks
    ---------------------------------------------------------------------------
    clk_10m_i          : in  std_logic;
    clk_62m5_i         : in  std_logic;

    ---------------------------------------------------------------------------
    -- Phase sample input (synchronous to clk_62m5_i)
    ---------------------------------------------------------------------------
    -- Rising edge at time t=0 (usually PPS or pps_csync_o) will sample the
    -- phase between the clocks.
    pps_csync_i        : in  std_logic;

    ---------------------------------------------------------------------------
    -- Measured Phase outputs (synchronous to clk_62m5_i)
    ---------------------------------------------------------------------------
    lock_sweep_o       : out std_logic;
    lock_sweep_phase_o : out std_logic_vector(4 downto 0)
    );

end entity auxclk_phase_sampler_10m;

architecture struct of auxclk_phase_sampler_10m is

  -----------------------------------------------------------------------------
  -- Signals
  -----------------------------------------------------------------------------
  -- 25 lock patterns "a"
  constant lock_pattern_1a : std_logic_vector(24 downto 0) := "0000111000111000111000111";
  constant lock_pattern_2a : std_logic_vector(24 downto 0) := "0001110000111000111000111";
  constant lock_pattern_3a : std_logic_vector(24 downto 0) := "0001110001110000111000111";
  constant lock_pattern_4a : std_logic_vector(24 downto 0) := "0001110001110001110000111";
  constant lock_pattern_5a : std_logic_vector(24 downto 0) := "0001110001110001110001110";
  constant lock_pattern_6a : std_logic_vector(24 downto 0) := "0011100001110001110001110";
  constant lock_pattern_7a : std_logic_vector(24 downto 0) := "0011100011100001110001110";
  constant lock_pattern_8a : std_logic_vector(24 downto 0) := "0011100011100011100001110";
  constant lock_pattern_9a : std_logic_vector(24 downto 0) := "0011100011100011100011100";
  constant lock_pattern_10a : std_logic_vector(24 downto 0) := "0111000011100011100011100";
  constant lock_pattern_11a : std_logic_vector(24 downto 0) := "0111000111000011100011100";
  constant lock_pattern_12a : std_logic_vector(24 downto 0) := "0111000111000111000011100";
  constant lock_pattern_13a : std_logic_vector(24 downto 0) := "0111000111000111000111000";
  constant lock_pattern_14a : std_logic_vector(24 downto 0) := "1110000111000111000111000";
  constant lock_pattern_15a : std_logic_vector(24 downto 0) := "1110001110000111000111000";
  constant lock_pattern_16a : std_logic_vector(24 downto 0) := "1110001110001110000111000";
  constant lock_pattern_17a : std_logic_vector(24 downto 0) := "1110001110001110001110000";
  constant lock_pattern_18a : std_logic_vector(24 downto 0) := "1100001110001110001110001";
  constant lock_pattern_19a : std_logic_vector(24 downto 0) := "1100011100001110001110001";
  constant lock_pattern_20a : std_logic_vector(24 downto 0) := "1100011100011100001110001";
  constant lock_pattern_21a : std_logic_vector(24 downto 0) := "1100011100011100011100001";
  constant lock_pattern_22a : std_logic_vector(24 downto 0) := "1000011100011100011100011";
  constant lock_pattern_23a : std_logic_vector(24 downto 0) := "1000111000011100011100011";
  constant lock_pattern_24a : std_logic_vector(24 downto 0) := "1000111000111000011100011";
  constant lock_pattern_25a : std_logic_vector(24 downto 0) := "1000111000111000111000011";
  
  -- 25 lock patterns "b"
  constant lock_pattern_1b : std_logic_vector(24 downto 0) := "1000111000111000111000111";
  constant lock_pattern_2b : std_logic_vector(24 downto 0) := "0001111000111000111000111";
  constant lock_pattern_3b : std_logic_vector(24 downto 0) := "0001110001111000111000111";
  constant lock_pattern_4b : std_logic_vector(24 downto 0) := "0001110001110001111000111";
  constant lock_pattern_5b : std_logic_vector(24 downto 0) := "0001110001110001110001111";
  constant lock_pattern_6b : std_logic_vector(24 downto 0) := "0011110001110001110001110";
  constant lock_pattern_7b : std_logic_vector(24 downto 0) := "0011100011110001110001110";
  constant lock_pattern_8b : std_logic_vector(24 downto 0) := "0011100011100011110001110";
  constant lock_pattern_9b : std_logic_vector(24 downto 0) := "0011100011100011100011110";
  constant lock_pattern_10b : std_logic_vector(24 downto 0) := "0111100011100011100011100";
  constant lock_pattern_11b : std_logic_vector(24 downto 0) := "0111000111100011100011100";
  constant lock_pattern_12b : std_logic_vector(24 downto 0) := "0111000111000111100011100";
  constant lock_pattern_13b : std_logic_vector(24 downto 0) := "0111000111000111000111100";
  constant lock_pattern_14b : std_logic_vector(24 downto 0) := "1111000111000111000111000";
  constant lock_pattern_15b : std_logic_vector(24 downto 0) := "1110001111000111000111000";
  constant lock_pattern_16b : std_logic_vector(24 downto 0) := "1110001110001111000111000";
  constant lock_pattern_17b : std_logic_vector(24 downto 0) := "1110001110001110001111000";
  constant lock_pattern_18b : std_logic_vector(24 downto 0) := "1110001110001110001110001";
  constant lock_pattern_19b : std_logic_vector(24 downto 0) := "1100011110001110001110001";
  constant lock_pattern_20b : std_logic_vector(24 downto 0) := "1100011100011110001110001";
  constant lock_pattern_21b : std_logic_vector(24 downto 0) := "1100011100011100011110001";
  constant lock_pattern_22b : std_logic_vector(24 downto 0) := "1100011100011100011100011";
  constant lock_pattern_23b : std_logic_vector(24 downto 0) := "1000111100011100011100011";
  constant lock_pattern_24b : std_logic_vector(24 downto 0) := "1000111000111100011100011";
  constant lock_pattern_25b : std_logic_vector(24 downto 0) := "1000111000111000111100011";

  signal sampled_10m          : std_logic;
  signal shift_reg            : std_logic_vector(24 downto 0) := (others => '0');
  signal captured_pattern     : std_logic_vector(24 downto 0) := (others => '0');
  signal lock_sweep_phase     : std_logic_vector(4 downto 0) := (others => '0');

begin
  
  U_sample_62m5 : gc_sync_ffs
    generic map (
      g_sync_edge => "positive")
    port map (
      clk_i    => clk_62m5_i,
      rst_n_i  => '1',
      data_i   => clk_10m_i,
      synced_o => sampled_10m);

  p_quantify_phase : process(clk_62m5_i)
  begin
    if rising_edge(clk_62m5_i) then

      shift_reg <= sampled_10m & shift_reg(shift_reg'high downto shift_reg'low + 1);

      if pps_csync_i = '1' then
        captured_pattern <= shift_reg;
      end if;
    end if;
  end process;

  p_phase_mux : process(captured_pattern)
  begin
    case captured_pattern is
      when lock_pattern_1a | lock_pattern_1b => lock_sweep_phase <= std_logic_vector(to_unsigned(1,lock_sweep_phase'length));
      when lock_pattern_2a | lock_pattern_2b => lock_sweep_phase <= std_logic_vector(to_unsigned(2,lock_sweep_phase'length));
      when lock_pattern_3a | lock_pattern_3b => lock_sweep_phase <= std_logic_vector(to_unsigned(3,lock_sweep_phase'length));
      when lock_pattern_4a | lock_pattern_4b => lock_sweep_phase <= std_logic_vector(to_unsigned(4,lock_sweep_phase'length));
      when lock_pattern_5a | lock_pattern_5b => lock_sweep_phase <= std_logic_vector(to_unsigned(5,lock_sweep_phase'length));
      when lock_pattern_6a | lock_pattern_6b => lock_sweep_phase <= std_logic_vector(to_unsigned(6,lock_sweep_phase'length));
      when lock_pattern_7a | lock_pattern_7b => lock_sweep_phase <= std_logic_vector(to_unsigned(7,lock_sweep_phase'length));
      when lock_pattern_8a | lock_pattern_8b => lock_sweep_phase <= std_logic_vector(to_unsigned(8,lock_sweep_phase'length));
      when lock_pattern_9a | lock_pattern_9b => lock_sweep_phase <= std_logic_vector(to_unsigned(9,lock_sweep_phase'length));
      when lock_pattern_10a | lock_pattern_10b => lock_sweep_phase <= std_logic_vector(to_unsigned(10,lock_sweep_phase'length));
      when lock_pattern_11a | lock_pattern_11b => lock_sweep_phase <= std_logic_vector(to_unsigned(11,lock_sweep_phase'length));
      when lock_pattern_12a | lock_pattern_12b => lock_sweep_phase <= std_logic_vector(to_unsigned(12,lock_sweep_phase'length));
      when lock_pattern_13a | lock_pattern_13b => lock_sweep_phase <= std_logic_vector(to_unsigned(13,lock_sweep_phase'length));
      when lock_pattern_14a | lock_pattern_14b => lock_sweep_phase <= std_logic_vector(to_unsigned(14,lock_sweep_phase'length));
      when lock_pattern_15a | lock_pattern_15b => lock_sweep_phase <= std_logic_vector(to_unsigned(15,lock_sweep_phase'length));
      when lock_pattern_16a | lock_pattern_16b => lock_sweep_phase <= std_logic_vector(to_unsigned(16,lock_sweep_phase'length));
      when lock_pattern_17a | lock_pattern_17b => lock_sweep_phase <= std_logic_vector(to_unsigned(17,lock_sweep_phase'length));
      when lock_pattern_18a | lock_pattern_18b => lock_sweep_phase <= std_logic_vector(to_unsigned(18,lock_sweep_phase'length));
      when lock_pattern_19a | lock_pattern_19b => lock_sweep_phase <= std_logic_vector(to_unsigned(19,lock_sweep_phase'length));
      when lock_pattern_20a | lock_pattern_20b => lock_sweep_phase <= std_logic_vector(to_unsigned(20,lock_sweep_phase'length));
      when lock_pattern_21a | lock_pattern_21b => lock_sweep_phase <= std_logic_vector(to_unsigned(21,lock_sweep_phase'length));
      when lock_pattern_22a | lock_pattern_22b => lock_sweep_phase <= std_logic_vector(to_unsigned(22,lock_sweep_phase'length));
      when lock_pattern_23a | lock_pattern_23b => lock_sweep_phase <= std_logic_vector(to_unsigned(23,lock_sweep_phase'length));
      when lock_pattern_24a | lock_pattern_24b => lock_sweep_phase <= std_logic_vector(to_unsigned(24,lock_sweep_phase'length));
      when lock_pattern_25a | lock_pattern_25b => lock_sweep_phase <= std_logic_vector(to_unsigned(25,lock_sweep_phase'length));
      when others =>
        lock_sweep_phase <= std_logic_vector(to_unsigned(0,lock_sweep_phase'length));
    end case;
  end process;

  lock_sweep_o <= '0' when (lock_sweep_phase = std_logic_vector(to_unsigned(1,lock_sweep_phase'length))) else '1';
  lock_sweep_phase_o <= lock_sweep_phase;

end architecture struct;