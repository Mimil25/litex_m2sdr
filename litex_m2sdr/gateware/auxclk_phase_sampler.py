import numpy as np

from migen import *
from migen.genlib.cdc import *

from litex.gen import *

def gen_lut(freq_a=10e6, freq_b=62.5e6):
    p_a = round(1e12/freq_a) # ps
    p_b = round(1e12/freq_b) # ps
    lcm = np.lcm(p_a, p_b)
    m_a = int(lcm // p_b)
    m_b = int(lcm // p_a)
    ps_unit = p_a / m_a
    print(f"{m_a} possible phase positions, phase shifts of {ps_unit} ps")
    lut = []
    for ps in np.arange(0, p_a, ps_unit/2): # ps iter over possible lock positions
        pattern = []
        for t in range(0, lcm, p_b): # t iter over clk_b rising edges to sample clk_a
            clk_a = 1 if (t + ps) % p_a >= p_a / 2 else 0
            pattern.append(clk_a)
        lut.append((ps, pattern)) 
    return lut, m_a, ps_unit

def val_for_pattern(pat): # pat is a list of integers, 0s and 1s
    return int(''.join(map(str, pat)), 2)

class AuxClkPhaseSampler(LiteXModule):
    def __init__(self, freq_aux, freq_sampler=62.5e6):
        self.aux_clk = Signal() # aux clk input
        self.csync_pps = Signal() # PPS input
        
        size_phase = 8
        self.locksweep_phase = Signal(size_phase)
        self.locksweep_phase_new = Signal()

        lut, m_a, ps_unit = gen_lut(freq_aux, freq_sampler)

        # -- sampler
        sampled = Signal()
        self.specials += MultiReg(
                i = self.aux_clk,
                o = sampled,
                )

        shift_reg = Signal(m_a)
        self.sync += shift_reg.eq(Cat(shift_reg[1:], sampled))

        pattern = Signal(m_a)
        counter = Signal(size_phase)
        self.sync += counter.eq(Mux((counter == 0) | self.csync_pps,
                                    m_a - 1,
                                    counter - 1))
        
        self.sync += If(counter == 0,
                        pattern.eq(shift_reg))

        self.sync += [If((pattern == val_for_pattern(lut[i*2][1])) | (pattern == val_for_pattern(lut[i*2-1][1])),
                          self.locksweep_phase.eq(i + 1)) for i in range(m_a)]

                     
# ------------- Below is not relevent for LiteX


def print_luts(lut):
    m_a = len(lut)//2
    ps_unit = lut[2][0]
    # print simple lut
    f = lambda p : (p-64e3)/ps_unit * 2**12
    print("simple lut :")
    for i in range(m_a):
        print(*lut[i*2][1], sep='', end=' or ')
        print(*lut[i*2-1][1], sep='', end=' => ')
        print(lut[i*2][0], 'ps', end='\t: ')
        print(f(lut[i*2][0]))
    # print peter lut
    print("peter lut :")
    for i in range(m_a):
        j = (i * 21 + 16) % m_a
        print(*lut[j*2][1], sep='', end=' or ')
        print(*lut[j*2-1][1], sep='', end=' => ')
        print(lut[j*2][0], 'ps', end='\t: ')
        print(f(lut[j*2][0]))

def freq_str(f):
    return str(f/1e6).replace('.', 'm').rstrip('0')

def gen_vhd(freq_a, freq_b=62.5e6, filename=None):
    lut, m_a, ps_unit = gen_lut(freq_a, freq_b)
    f_a = freq_str(freq_a)
    f_b = freq_str(freq_b)
    template = f"""library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.gencores_pkg.all;

entity auxclk_phase_sampler_{f_a} is
  port (
    ---------------------------------------------------------------------------
    -- Clocks
    ---------------------------------------------------------------------------
    clk_{f_a}_i          : in  std_logic;
    clk_{f_b}_i         : in  std_logic;

    ---------------------------------------------------------------------------
    -- Phase sample input (synchronous to clk_{f_b}_i)
    ---------------------------------------------------------------------------
    -- Rising edge at time t=0 (usually PPS or pps_csync_o) will sample the
    -- phase between the clocks.
    pps_csync_i        : in  std_logic;

    ---------------------------------------------------------------------------
    -- Measured Phase outputs (synchronous to clk_{f_b}_i)
    ---------------------------------------------------------------------------
    lock_sweep_o       : out std_logic;
    lock_sweep_phase_o : out std_logic_vector(4 downto 0)
    );

end entity auxclk_phase_sampler_{f_a};

architecture struct of auxclk_phase_sampler_{f_a} is

  -----------------------------------------------------------------------------
  -- Signals
  -----------------------------------------------------------------------------
  -- {m_a} lock patterns "a"
{'\n'.join(f'  constant lock_pattern_{i+1}a : std_logic_vector({m_a-1} downto 0) := "{''.join(map(str,lut[i*2][1]))}";' for i in range(m_a))}
  
  -- {m_a} lock patterns "b"
{'\n'.join(f'  constant lock_pattern_{i+1}b : std_logic_vector({m_a-1} downto 0) := "{''.join(map(str,lut[i*2-1][1]))}";' for i in range(m_a))}

  signal sampled_{f_a}          : std_logic;
  signal shift_reg            : std_logic_vector({m_a-1} downto 0) := (others => '0');
  signal captured_pattern     : std_logic_vector({m_a-1} downto 0) := (others => '0');
  signal lock_sweep_phase     : std_logic_vector(4 downto 0) := (others => '0');

begin
  
  U_sample_62m5 : gc_sync_ffs
    generic map (
      g_sync_edge => "positive")
    port map (
      clk_i    => clk_{f_b}_i,
      rst_n_i  => '1',
      data_i   => clk_{f_a}_i,
      synced_o => sampled_{f_a});

  p_quantify_phase : process(clk_{f_b}_i)
  begin
    if rising_edge(clk_{f_b}_i) then

      shift_reg <= sampled_{f_a} & shift_reg(shift_reg'high downto shift_reg'low + 1);

      if pps_csync_i = '1' then
        captured_pattern <= shift_reg;
      end if;
    end if;
  end process;

  p_phase_mux : process(captured_pattern)
  begin
    case captured_pattern is
{'\n'.join(f"      when lock_pattern_{i+1}a | lock_pattern_{i+1}b => lock_sweep_phase <= std_logic_vector(to_unsigned({i+1},lock_sweep_phase'length));" for i in range(m_a))}
      when others =>
        lock_sweep_phase <= std_logic_vector(to_unsigned(0,lock_sweep_phase'length));
    end case;
  end process;

  lock_sweep_o <= '0' when (lock_sweep_phase = std_logic_vector(to_unsigned(1,lock_sweep_phase'length))) else '1';
  lock_sweep_phase_o <= lock_sweep_phase;

end architecture struct;"""
    if filename is None:
        filename = f"auxclk_phase_sampler_{freq_str(freq_a)}.vhd"
    with open(filename, 'w') as file:
        file.write(template)
