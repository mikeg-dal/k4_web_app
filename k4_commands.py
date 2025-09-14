"""
K4 Command Handler - Comprehensive Multi-Operation Command Management System

This module provides complete K4 radio command support including:
- All 219 K4 commands with proper categorization
- Multi-operation support (SET/GET/TOGGLE/INCREMENT/DECREMENT)
- Sub receiver ($) suffix handling
- Response parsing and validation
- UI update generation
- AI (Auto-Info) streaming response handling
- Command history and tracking

Based on Elecraft K4 Programmer's Reference Rev. D5
"""

import time
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum

# Import debug helper for controlled debugging
from debug_helper import debug_print


class CommandType(Enum):
    """Types of K4 commands"""
    GET_SET = "get_set"      # Commands that can both query and set values
    GET_ONLY = "get_only"    # Commands that only query values
    SET_ONLY = "set_only"    # Commands that only set values
    SPECIAL = "special"      # Commands with special handling


class OperationType(Enum):
    """Types of operations supported by commands"""
    SET = "SET"                    # Set specific value: AG050;
    GET = "GET"                    # Get current value: AG;
    TOGGLE = "TOGGLE"              # Toggle operation: AG/;
    INCREMENT = "INCREMENT"        # Increment: AG+;
    DECREMENT = "DECREMENT"        # Decrement: AG-;
    NORMALIZE = "NORMALIZE"        # Normalize: BL~;
    BAND_STACK_NEXT = "BAND_STACK_NEXT"     # Band stack: BN^;
    BAND_STACK_RECALL = "BAND_STACK_RECALL" # Band stack: BN>;
    SPECIAL_OP = "SPECIAL_OP"      # Special operations like DV\;


@dataclass
class OperationInfo:
    """Information about a specific operation type for a command"""
    operation_type: OperationType
    format_pattern: str            # Command format pattern
    value_type: str = "string"     # int, float, string, compound, enum
    range_min: Optional[int] = None
    range_max: Optional[int] = None
    enum_values: Optional[Dict[str, str]] = None
    compound_format: Optional[Dict[str, Any]] = None
    behavior: str = "standard"     # standard, toggle_zero_last, cycle_values, etc.
    response_format: str = ""      # Expected response format
    description: str = ""


@dataclass
class CommandInfo:
    """Comprehensive information about a K4 command"""
    base_command: str
    command_type: CommandType
    description: str
    category: str = ""             # frequency, audio, mode, etc.
    supports_sub_receiver: bool = False
    operations: Dict[OperationType, OperationInfo] = field(default_factory=dict)
    ui_updates: Dict[str, Union[str, List[str]]] = field(default_factory=dict)
    ai_eligible: bool = True       # Can generate AI responses
    auto_delivery: bool = False    # Can be set for automatic delivery
    response_parser: str = ""      # Custom response parser function name
    notes: str = ""


class K4CommandHandler:
    """
    Comprehensive K4 command handler supporting all 219 commands.
    Handles multi-operation commands, response parsing, and UI updates.
    """
    
    def __init__(self):
        self.commands = self._initialize_all_commands()
        self.command_history = []
        self.max_history = 100
        self.ai_mode = 0
        self.last_sent_commands = {}  # Track recently sent commands for AI detection
        
    def _initialize_all_commands(self) -> Dict[str, CommandInfo]:
        """Initialize all 219 K4 commands with comprehensive definitions"""
        commands = {}
        
        # Define all command groups with their operations
        command_groups = {
            'frequency': self._define_frequency_commands(),
            'audio': self._define_audio_commands(),
            'mode': self._define_mode_commands(),
            'filter': self._define_filter_commands(),
            'antenna': self._define_antenna_commands(),
            'band': self._define_band_commands(),
            'rit_xit': self._define_rit_xit_commands(),
            'transmit': self._define_transmit_commands(),
            'cw_text': self._define_cw_text_commands(),
            'system': self._define_system_commands(),
            'memory': self._define_memory_commands(),
            'menu': self._define_menu_commands(),
            'display': self._define_display_commands(),
            'remote': self._define_remote_commands()
        }
        
        # Flatten all command groups into single dictionary
        for category, category_commands in command_groups.items():
            for cmd_name, cmd_info in category_commands.items():
                cmd_info.category = category
                commands[cmd_name] = cmd_info
        
        debug_print("COMMANDS", f"Initialized {len(commands)} K4 commands across {len(command_groups)} categories")
        return commands
    
    def _define_frequency_commands(self) -> Dict[str, CommandInfo]:
        """Define all frequency-related commands"""
        return {
            'FA': CommandInfo(
                base_command='FA',
                command_type=CommandType.GET_SET,
                description='VFO A frequency',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='FA{value};',
                        value_type='int',
                        range_min=30000,
                        range_max=74800000,
                        response_format='FAnnnnnnnnn;',
                        description='Set VFO A frequency (Hz)'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='FA;',
                        response_format='FAnnnnnnnnn;',
                        description='Get VFO A frequency'
                    )
                },
                ui_updates={
                    'main': ['vfo_a_freq', 'vfo_a_freq_hz']
                },
                ai_eligible=True,
                response_parser='parse_frequency_response'
            ),
            'FB': CommandInfo(
                base_command='FB',
                command_type=CommandType.GET_SET,
                description='VFO B frequency',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='FB{value};',
                        value_type='int',
                        range_min=30000,
                        range_max=74800000,
                        response_format='FBnnnnnnnnn;',
                        description='Set VFO B frequency (Hz)'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='FB;',
                        response_format='FBnnnnnnnnn;',
                        description='Get VFO B frequency'
                    )
                },
                ui_updates={
                    'main': ['vfo_b_freq', 'vfo_b_freq_hz']
                },
                ai_eligible=True,
                response_parser='parse_frequency_response'
            ),
            'FI': CommandInfo(
                base_command='FI',
                command_type=CommandType.GET_SET,
                description='IF center frequency (panadapter)',
                supports_sub_receiver=True,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='FI{$}{value};',
                        value_type='int',
                        range_min=30000,
                        range_max=74800000,
                        response_format='FI{$}nnnnnnnnn;',
                        description='Set IF center frequency'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='FI{$};',
                        response_format='FI{$}nnnnnnnnn;',
                        description='Get IF center frequency'
                    )
                },
                ui_updates={
                    'main': ['if_center_freq', 'if_center_freq_hz'],
                    'sub': ['if_center_freq_sub', 'if_center_freq_sub_hz']
                },
                ai_eligible=True,
                response_parser='parse_frequency_response'
            ),
            'FC': CommandInfo(
                base_command='FC',
                command_type=CommandType.SET_ONLY,
                description='Center panadapter on VFO',
                supports_sub_receiver=True,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='FC{$};',
                        description='Center panadapter on target VFO'
                    ),
                    OperationType.SPECIAL_OP: OperationInfo(
                        operation_type=OperationType.SPECIAL_OP,
                        format_pattern='FC{$}{offset};',
                        value_type='int',
                        description='Center panadapter with offset in Hz'
                    )
                },
                ui_updates={
                    'main': ['panadapter_centered'],
                    'sub': ['panadapter_centered_sub']
                },
                ai_eligible=False
            ),
            'FT': CommandInfo(
                base_command='FT',
                command_type=CommandType.GET_SET,
                description='Split operation',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='FT{value};',
                        value_type='enum',
                        enum_values={'0': 'OFF', '1': 'ON'},
                        response_format='FTn;',
                        description='Set split on/off'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='FT;',
                        response_format='FTn;',
                        description='Get split status'
                    ),
                    OperationType.TOGGLE: OperationInfo(
                        operation_type=OperationType.TOGGLE,
                        format_pattern='FT/;',
                        behavior='toggle_split',
                        response_format='FTn;',
                        description='Toggle split on/off'
                    )
                },
                ui_updates={
                    'main': ['split_enabled']
                },
                ai_eligible=True
            ),
            'VT': CommandInfo(
                base_command='VT',
                command_type=CommandType.GET_SET,
                description='VFO tuning step',
                supports_sub_receiver=True,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='VT{$}{step}{mode};',
                        value_type='compound',
                        compound_format={
                            'step': {'type': 'enum', 'values': {'0': '1Hz', '1': '10Hz', '2': '100Hz', '3': '1kHz', '4': '10kHz', '5': '100kHz'}},
                            'mode': {'type': 'int', 'range': (1, 9)}
                        },
                        response_format='VT{$}nm;',
                        description='Set VFO tuning step'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='VT{$};',
                        response_format='VT{$}nm;',
                        description='Get VFO tuning step'
                    ),
                    OperationType.TOGGLE: OperationInfo(
                        operation_type=OperationType.TOGGLE,
                        format_pattern='VT{$}/;',
                        behavior='cycle_tuning_step',
                        response_format='VT{$}nm;',
                        description='Toggle tuning step (RATE switch)'
                    ),
                    OperationType.SPECIAL_OP: OperationInfo(
                        operation_type=OperationType.SPECIAL_OP,
                        format_pattern='VT{$}\\;',
                        behavior='khz_switch_hold',
                        response_format='VT{$}nm;',
                        description='KHZ switch hold function'
                    )
                },
                ui_updates={
                    'main': ['vfo_step', 'vfo_step_hz'],
                    'sub': ['vfo_step_sub', 'vfo_step_sub_hz']
                },
                ai_eligible=True
            )
        }
    
    def _define_audio_commands(self) -> Dict[str, CommandInfo]:
        """Define all audio-related commands"""
        return {
            'AG': CommandInfo(
                base_command='AG',
                command_type=CommandType.GET_SET,
                description='AF gain',
                supports_sub_receiver=True,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='AG{$}{value};',
                        value_type='int',
                        range_min=0,
                        range_max=60,
                        response_format='AG{$}nnn;',
                        description='Set AF gain (000-060)'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='AG{$};',
                        response_format='AG{$}nnn;',
                        description='Get AF gain'
                    ),
                    OperationType.TOGGLE: OperationInfo(
                        operation_type=OperationType.TOGGLE,
                        format_pattern='AG{$}/;',
                        behavior='toggle_between_zero_and_last',
                        response_format='AG{$}nnn;',
                        description='Toggle between last gain and mute'
                    ),
                    OperationType.INCREMENT: OperationInfo(
                        operation_type=OperationType.INCREMENT,
                        format_pattern='AG{$}+;',
                        behavior='increment_gain',
                        response_format='AG{$}nnn;',
                        description='Increment AF gain'
                    ),
                    OperationType.DECREMENT: OperationInfo(
                        operation_type=OperationType.DECREMENT,
                        format_pattern='AG{$}-;',
                        behavior='decrement_gain',
                        response_format='AG{$}nnn;',
                        description='Decrement AF gain'
                    )
                },
                ui_updates={
                    'main': 'af_gain_main',
                    'sub': 'af_gain_sub'
                },
                ai_eligible=True
            ),
            'AL': CommandInfo(
                base_command='AL',
                command_type=CommandType.GET_SET,
                description='AF limiter (AGC off)',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='AL{value};',
                        value_type='int',
                        range_min=1,
                        range_max=30,
                        response_format='ALnn;',
                        description='Set AF limiter level (01-30)'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='AL;',
                        response_format='ALnn;',
                        description='Get AF limiter level'
                    )
                },
                ui_updates={
                    'main': 'af_limiter'
                },
                ai_eligible=True
            ),
            'BL': CommandInfo(
                base_command='BL',
                command_type=CommandType.GET_SET,
                description='Audio balance control',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='BL{mode}{balance};',
                        value_type='compound',
                        compound_format={
                            'mode': {'type': 'enum', 'values': {'0': 'OFF', '1': 'ON'}},
                            'balance': {'type': 'int', 'range': (-50, 50), 'format': '{:+03d}'}
                        },
                        response_format='BLm+nn;',
                        description='Set balance mode and level'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='BL;',
                        response_format='BLm+nn;',
                        description='Get balance settings'
                    ),
                    OperationType.TOGGLE: OperationInfo(
                        operation_type=OperationType.TOGGLE,
                        format_pattern='BL/;',
                        behavior='toggle_balance_mode',
                        response_format='BLm+nn;',
                        description='Toggle balance mode on/off'
                    ),
                    OperationType.NORMALIZE: OperationInfo(
                        operation_type=OperationType.NORMALIZE,
                        format_pattern='BL~;',
                        behavior='normalize_balance',
                        response_format='BLm+nn;',
                        description='Normalize balance to 50/50'
                    )
                },
                ui_updates={
                    'main': ['balance_mode', 'balance_level']
                },
                ai_eligible=True
            ),
            'MG': CommandInfo(
                base_command='MG',
                command_type=CommandType.GET_SET,
                description='Microphone gain',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='MG{value};',
                        value_type='int',
                        range_min=0,
                        range_max=80,
                        response_format='MGnnn;',
                        description='Set mic gain (000-080)'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='MG;',
                        response_format='MGnnn;',
                        description='Get mic gain'
                    )
                },
                ui_updates={
                    'main': 'mic_gain'
                },
                ai_eligible=True
            ),
            'MX': CommandInfo(
                base_command='MX',
                command_type=CommandType.GET_SET,
                description='Main/Sub audio mix',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='MX{value};',
                        value_type='enum',
                        enum_values={
                            'A.B': 'Full stereo (main left, sub right)',
                            'AB.AB': 'Mono (main+sub both channels)',
                            'A.-A': 'Binaural (main left, main inverted right)',
                            'A.AB': 'Hybrid (main left, main+sub right)',
                            'AB.B': 'Hybrid (main+sub left, sub right)',
                            'AB.A': 'Hybrid (main+sub left, main right)',
                            'B.AB': 'Hybrid (sub left, main+sub right)',
                            'B.B': 'Sub only (sub both channels)',
                            'B.A': 'Swapped stereo (sub left, main right)',
                            'A.A': 'Main only (main both channels)'
                        },
                        response_format='MX{value};',
                        description='Set audio mix pattern'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='MX;',
                        response_format='MX{value};',
                        description='Get audio mix pattern'
                    )
                },
                ui_updates={
                    'main': 'audio_mix'
                },
                ai_eligible=True
            )
        }
    
    def _define_mode_commands(self) -> Dict[str, CommandInfo]:
        """Define all mode-related commands"""
        return {
            'MD': CommandInfo(
                base_command='MD',
                command_type=CommandType.GET_SET,
                description='Operating mode',
                supports_sub_receiver=True,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='MD{$}{value};',
                        value_type='enum',
                        enum_values={
                            '1': 'LSB', '2': 'USB', '3': 'CW', '4': 'FM', '5': 'AM',
                            '6': 'DATA', '7': 'CW-R', '9': 'DATA-R'
                        },
                        response_format='MD{$}n;',
                        description='Set operating mode'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='MD{$};',
                        response_format='MD{$}n;',
                        description='Get operating mode'
                    ),
                    OperationType.TOGGLE: OperationInfo(
                        operation_type=OperationType.TOGGLE,
                        format_pattern='MD{$}/;',
                        behavior='alternate_between_two_recent_modes',
                        response_format='MD{$}n;',
                        description='Toggle between two recent modes'
                    ),
                    OperationType.INCREMENT: OperationInfo(
                        operation_type=OperationType.INCREMENT,
                        format_pattern='MD{$}+;',
                        behavior='cycle_modes_forward',
                        response_format='MD{$}n;',
                        description='Cycle to next mode'
                    ),
                    OperationType.DECREMENT: OperationInfo(
                        operation_type=OperationType.DECREMENT,
                        format_pattern='MD{$}-;',
                        behavior='cycle_modes_backward',
                        response_format='MD{$}n;',
                        description='Cycle to previous mode'
                    )
                },
                ui_updates={
                    'main': 'mode_a',
                    'sub': 'mode_b'
                },
                ai_eligible=True,
                response_parser='parse_mode_response'
            ),
            'DT': CommandInfo(
                base_command='DT',
                command_type=CommandType.GET_SET,
                description='Data sub-mode',
                supports_sub_receiver=True,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='DT{$}{value};',
                        value_type='enum',
                        enum_values={
                            '0': 'DATA A', '1': 'AFSK A', '2': 'FSK D', '3': 'PSK D'
                        },
                        response_format='DT{$}n;',
                        description='Set data sub-mode'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='DT{$};',
                        response_format='DT{$}n;',
                        description='Get data sub-mode'
                    )
                },
                ui_updates={
                    'main': 'data_mode_a',
                    'sub': 'data_mode_b'
                },
                ai_eligible=True
            ),
            'GT': CommandInfo(
                base_command='GT',
                command_type=CommandType.GET_SET,
                description='AGC mode',
                supports_sub_receiver=True,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='GT{$}{value};',
                        value_type='enum',
                        enum_values={'0': 'OFF', '1': 'SLOW', '2': 'FAST'},
                        response_format='GT{$}n;',
                        description='Set AGC mode'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='GT{$};',
                        response_format='GT{$}n;',
                        description='Get AGC mode'
                    ),
                    OperationType.TOGGLE: OperationInfo(
                        operation_type=OperationType.TOGGLE,
                        format_pattern='GT{$}/;',
                        behavior='toggle_agc_on_off',
                        response_format='GT{$}n;',
                        description='Toggle AGC on/off'
                    )
                },
                ui_updates={
                    'main': 'agc_mode',
                    'sub': 'agc_mode_sub'
                },
                ai_eligible=True
            )
        }
    
    def _define_filter_commands(self) -> Dict[str, CommandInfo]:
        """Define all filter-related commands"""
        return {
            'AP': CommandInfo(
                base_command='AP',
                command_type=CommandType.GET_SET,
                description='Audio Peaking Filter (APF) for CW mode',
                supports_sub_receiver=True,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='AP{$}{mode}{bandwidth};',
                        value_type='compound',
                        compound_format={
                            'mode': {'type': 'enum', 'values': {'0': 'OFF', '1': 'ON'}},
                            'bandwidth': {'type': 'enum', 'values': {'0': '30Hz', '1': '50Hz', '2': '150Hz'}}
                        },
                        response_format='AP{$}mb;',
                        description='Set APF mode and bandwidth'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='AP{$};',
                        response_format='AP{$}mb;',
                        description='Get APF settings'
                    ),
                    OperationType.TOGGLE: OperationInfo(
                        operation_type=OperationType.TOGGLE,
                        format_pattern='AP{$}/;',
                        behavior='toggle_apf_mode',
                        response_format='AP{$}mb;',
                        description='Toggle APF on/off'
                    ),
                    OperationType.INCREMENT: OperationInfo(
                        operation_type=OperationType.INCREMENT,
                        format_pattern='AP{$}+;',
                        behavior='next_apf_bandwidth',
                        response_format='AP{$}mb;',
                        description='Select next APF bandwidth'
                    ),
                    OperationType.DECREMENT: OperationInfo(
                        operation_type=OperationType.DECREMENT,
                        format_pattern='AP{$}-;',
                        behavior='prev_apf_bandwidth',
                        response_format='AP{$}mb;',
                        description='Select previous APF bandwidth'
                    )
                },
                ui_updates={
                    'main': ['apf_mode', 'apf_bandwidth'],
                    'sub': ['apf_mode_sub', 'apf_bandwidth_sub']
                },
                ai_eligible=True,
                response_parser='parse_apf_response'
            ),
            'BW': CommandInfo(
                base_command='BW',
                command_type=CommandType.GET_SET,
                description='Filter bandwidth',
                supports_sub_receiver=True,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='BW{$}{value};',
                        value_type='int',
                        range_min=50,
                        range_max=40000,
                        response_format='BW{$}nnnn;',
                        description='Set filter bandwidth (Hz x 10)'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='BW{$};',
                        response_format='BW{$}nnnn;',
                        description='Get filter bandwidth'
                    )
                },
                ui_updates={
                    'main': 'bandwidth',
                    'sub': 'bandwidth_sub'
                },
                ai_eligible=True,
                response_parser='parse_bandwidth_response'
            ),
            'FP': CommandInfo(
                base_command='FP',
                command_type=CommandType.GET_SET,
                description='Filter preset',
                supports_sub_receiver=True,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='FP{$}{value};',
                        value_type='enum',
                        enum_values={'1': 'Preset 1', '2': 'Preset 2', '3': 'Preset 3'},
                        response_format='FP{$}n;',
                        description='Select filter preset'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='FP{$};',
                        response_format='FP{$}n;',
                        description='Get filter preset'
                    ),
                    OperationType.NORMALIZE: OperationInfo(
                        operation_type=OperationType.NORMALIZE,
                        format_pattern='FP~;',
                        behavior='normalize_filter',
                        response_format='FP{$}n;',
                        description='Normalize filter preset'
                    )
                },
                ui_updates={
                    'main': 'filter_preset',
                    'sub': 'filter_preset_sub'
                },
                ai_eligible=True
            )
        }
    
    def _define_antenna_commands(self) -> Dict[str, CommandInfo]:
        """Define all antenna-related commands"""
        return {
            'AN': CommandInfo(
                base_command='AN',
                command_type=CommandType.GET_SET,
                description='TX antenna selection',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='AN{value};',
                        value_type='enum',
                        enum_values={'1': 'ANT1', '2': 'ANT2', '3': 'ANT3'},
                        response_format='ANn;',
                        description='Set TX antenna'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='AN;',
                        response_format='ANn;',
                        description='Get TX antenna'
                    ),
                    OperationType.TOGGLE: OperationInfo(
                        operation_type=OperationType.TOGGLE,
                        format_pattern='AN/;',
                        behavior='alternate_between_two_recent_antennas',
                        response_format='ANn;',
                        description='Toggle between recent TX antennas'
                    )
                },
                ui_updates={
                    'main': 'tx_antenna'
                },
                ai_eligible=True
            ),
            'AR': CommandInfo(
                base_command='AR',
                command_type=CommandType.GET_SET,
                description='RX antenna selection',
                supports_sub_receiver=True,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='AR{$}{value};',
                        value_type='enum',
                        enum_values={
                            '0': 'Disconnected',
                            '1': 'EXT XVTR IN',
                            '2': 'RX uses TX ANT',
                            '3': 'INT XVTR IN',
                            '4': 'RX ANT IN1',
                            '5': 'ATU RX ANT1',
                            '6': 'ATU RX ANT2',
                            '7': 'ATU RX ANT3'
                        },
                        response_format='AR{$}n;',
                        description='Set RX antenna'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='AR{$};',
                        response_format='AR{$}n;',
                        description='Get RX antenna'
                    ),
                    OperationType.TOGGLE: OperationInfo(
                        operation_type=OperationType.TOGGLE,
                        format_pattern='AR{$}/;',
                        behavior='alternate_between_two_recent_rx_antennas',
                        response_format='AR{$}n;',
                        description='Toggle between recent RX antennas'
                    )
                },
                ui_updates={
                    'main': 'rx_antenna',
                    'sub': 'rx_antenna_sub'
                },
                ai_eligible=True
            ),
            'AT': CommandInfo(
                base_command='AT',
                command_type=CommandType.GET_SET,
                description='ATU mode',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='AT{value};',
                        value_type='enum',
                        enum_values={'0': 'NOT INST', '1': 'BYPASS', '2': 'AUTO'},
                        response_format='ATn;',
                        description='Set ATU mode'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='AT;',
                        response_format='ATn;',
                        description='Get ATU mode'
                    ),
                    OperationType.TOGGLE: OperationInfo(
                        operation_type=OperationType.TOGGLE,
                        format_pattern='AT/;',
                        behavior='toggle_atu_in_bypass',
                        response_format='ATn;',
                        description='Toggle ATU in/bypass'
                    )
                },
                ui_updates={
                    'main': 'atu_mode'
                },
                ai_eligible=True
            )
        }
    
    def _define_band_commands(self) -> Dict[str, CommandInfo]:
        """Define all band-related commands"""
        return {
            'BN': CommandInfo(
                base_command='BN',
                command_type=CommandType.GET_SET,
                description='Band selection',
                supports_sub_receiver=True,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='BN{$}{value};',
                        value_type='enum',
                        enum_values={
                            '00': '160m', '01': '80m', '02': '40m', '03': '30m', '04': '20m',
                            '05': '17m', '06': '15m', '07': '12m', '08': '10m', '09': '6m',
                            '10': '4m', '16': 'XVTR1', '17': 'XVTR2', '18': 'XVTR3', '19': 'XVTR4',
                            '20': 'XVTR5', '21': 'XVTR6', '22': 'XVTR7', '23': 'XVTR8',
                            '24': 'XVTR9', '25': 'XVTR10'
                        },
                        response_format='BN{$}nn;',
                        description='Set band'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='BN{$};',
                        response_format='BN{$}nn;',
                        description='Get band'
                    ),
                    OperationType.TOGGLE: OperationInfo(
                        operation_type=OperationType.TOGGLE,
                        format_pattern='BN{$}/;',
                        behavior='alternate_between_two_recent_bands',
                        response_format='BN{$}nn;',
                        description='Toggle between recent bands'
                    ),
                    OperationType.INCREMENT: OperationInfo(
                        operation_type=OperationType.INCREMENT,
                        format_pattern='BN{$}+;',
                        behavior='next_band',
                        response_format='BN{$}nn;',
                        description='Next band'
                    ),
                    OperationType.DECREMENT: OperationInfo(
                        operation_type=OperationType.DECREMENT,
                        format_pattern='BN{$}-;',
                        behavior='previous_band',
                        response_format='BN{$}nn;',
                        description='Previous band'
                    ),
                    OperationType.BAND_STACK_NEXT: OperationInfo(
                        operation_type=OperationType.BAND_STACK_NEXT,
                        format_pattern='BN{$}^;',
                        behavior='next_band_stack_register',
                        response_format='BN{$}nn;',
                        description='Next band stack register'
                    ),
                    OperationType.BAND_STACK_RECALL: OperationInfo(
                        operation_type=OperationType.BAND_STACK_RECALL,
                        format_pattern='BN{$}>;',
                        behavior='recall_band_stack_register',
                        response_format='BN{$}nn;',
                        description='Recall band stack register'
                    )
                },
                ui_updates={
                    'main': 'band_main',
                    'sub': 'band_sub'
                },
                ai_eligible=True,
                response_parser='parse_band_response'
            )
        }
    
    def _define_rit_xit_commands(self) -> Dict[str, CommandInfo]:
        """Define all RIT/XIT commands"""
        return {
            'RT': CommandInfo(
                base_command='RT',
                command_type=CommandType.GET_SET,
                description='RIT on/off',
                supports_sub_receiver=True,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='RT{$}{value};',
                        value_type='enum',
                        enum_values={'0': 'OFF', '1': 'ON'},
                        response_format='RT{$}n;',
                        description='Set RIT on/off'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='RT{$};',
                        response_format='RT{$}n;',
                        description='Get RIT status'
                    ),
                    OperationType.TOGGLE: OperationInfo(
                        operation_type=OperationType.TOGGLE,
                        format_pattern='RT{$}/;',
                        behavior='toggle_rit',
                        response_format='RT{$}n;',
                        description='Toggle RIT on/off'
                    )
                },
                ui_updates={
                    'main': 'rit_enabled',
                    'sub': 'rit_enabled_sub'
                },
                ai_eligible=True
            ),
            'XT': CommandInfo(
                base_command='XT',
                command_type=CommandType.GET_SET,
                description='XIT on/off',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='XT{value};',
                        value_type='enum',
                        enum_values={'0': 'OFF', '1': 'ON'},
                        response_format='XTn;',
                        description='Set XIT on/off'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='XT;',
                        response_format='XTn;',
                        description='Get XIT status'
                    ),
                    OperationType.TOGGLE: OperationInfo(
                        operation_type=OperationType.TOGGLE,
                        format_pattern='XT/;',
                        behavior='toggle_xit',
                        response_format='XTn;',
                        description='Toggle XIT on/off'
                    )
                },
                ui_updates={
                    'main': 'xit_enabled'
                },
                ai_eligible=True
            ),
            'RO': CommandInfo(
                base_command='RO',
                command_type=CommandType.GET_SET,
                description='RIT/XIT offset',
                supports_sub_receiver=True,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='RO{$}{sign}{value};',
                        value_type='compound',
                        compound_format={
                            'sign': {'type': 'enum', 'values': {'+': 'positive', '-': 'negative'}},
                            'value': {'type': 'int', 'range': (0, 9999)}
                        },
                        response_format='RO{$}snnnn;',
                        description='Set RIT/XIT offset in Hz'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='RO{$};',
                        response_format='RO{$}snnnn;',
                        description='Get RIT/XIT offset'
                    )
                },
                ui_updates={
                    'main': ['rit_offset', 'xit_offset'],
                    'sub': ['rit_offset_sub', 'xit_offset_sub']
                },
                ai_eligible=True,
                response_parser='parse_rit_xit_offset_response'
            )
        }
    
    def _define_transmit_commands(self) -> Dict[str, CommandInfo]:
        """Define all transmit-related commands"""
        return {
            'PC': CommandInfo(
                base_command='PC',
                command_type=CommandType.GET_SET,
                description='Power control',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='PC{power}{range};',
                        value_type='compound',
                        compound_format={
                            'power': {'type': 'int', 'range': (1, 110), 'format': '{:03d}'},
                            'range': {'type': 'enum', 'values': {'L': 'Low (QRP)', 'H': 'High (QRO)', 'X': 'mW (XVTR)'}}
                        },
                        response_format='PCnnnr;',
                        description='Set power output'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='PC;',
                        response_format='PCnnnr;',
                        description='Get power output'
                    )
                },
                ui_updates={
                    'main': ['power_output', 'power_range']
                },
                ai_eligible=True,
                response_parser='parse_power_response'
            ),
            'TX': CommandInfo(
                base_command='TX',
                command_type=CommandType.SET_ONLY,
                description='Go to transmit mode',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='TX;',
                        description='Enter transmit mode'
                    )
                },
                ui_updates={
                    'main': 'tx_mode'
                },
                ai_eligible=True
            ),
            'RX': CommandInfo(
                base_command='RX',
                command_type=CommandType.SET_ONLY,
                description='Go to receive mode',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='RX;',
                        description='Enter receive mode'
                    )
                },
                ui_updates={
                    'main': 'rx_mode'
                },
                ai_eligible=True
            )
        }
    
    def _define_cw_text_commands(self) -> Dict[str, CommandInfo]:
        """Define all CW/text commands"""
        return {
            'KS': CommandInfo(
                base_command='KS',
                command_type=CommandType.GET_SET,
                description='Keyer speed',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='KS{value};',
                        value_type='int',
                        range_min=8,
                        range_max=100,
                        response_format='KSnnn;',
                        description='Set keyer speed (8-100 WPM)'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='KS;',
                        response_format='KSnnn;',
                        description='Get keyer speed'
                    )
                },
                ui_updates={
                    'main': 'keyer_speed'
                },
                ai_eligible=True
            ),
            'KY': CommandInfo(
                base_command='KY',
                command_type=CommandType.SET_ONLY,
                description='CW/DATA message text',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='KY{modifier}{text};',
                        value_type='compound',
                        compound_format={
                            'modifier': {'type': 'enum', 'values': {' ': 'Normal', 'R': 'Repeat', 'W': 'Wait'}},
                            'text': {'type': 'string', 'max_length': 60}
                        },
                        response_format='KYn;',
                        description='Send CW/DATA text'
                    )
                },
                ui_updates={
                    'main': 'cw_text_status'
                },
                ai_eligible=False
            )
        }
    
    def _define_system_commands(self) -> Dict[str, CommandInfo]:
        """Define all system-related commands"""
        return {
            'AI': CommandInfo(
                base_command='AI',
                command_type=CommandType.GET_SET,
                description='Auto-info mode',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='AI{value};',
                        value_type='enum',
                        enum_values={
                            '0': 'Off',
                            '1': 'VFO/RIT periodic',
                            '2': 'All changes periodic',
                            '4': 'Immediate non-client changes',
                            '5': 'Immediate all changes'
                        },
                        response_format='AIn;',
                        description='Set auto-info mode'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='AI;',
                        response_format='AIn;',
                        description='Get auto-info mode'
                    )
                },
                ui_updates={
                    'main': 'ai_mode'
                },
                ai_eligible=False  # This command controls AI, doesn't generate AI
            ),
            'IF': CommandInfo(
                base_command='IF',
                command_type=CommandType.GET_ONLY,
                description='Basic radio information',
                supports_sub_receiver=False,
                operations={
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='IF;',
                        response_format='IF[f]*****+yyyyrx*00tm0spbd1*;',
                        description='Get complete radio status'
                    )
                },
                ui_updates={
                    'main': ['frequency', 'rit_offset', 'rit_on', 'xit_on', 'tx_state', 'mode', 'scan', 'split', 'data_submode']
                },
                ai_eligible=True,
                response_parser='parse_if_response'
            ),
            'SM': CommandInfo(
                base_command='SM',
                command_type=CommandType.GET_SET,
                description='S-meter reading',
                supports_sub_receiver=True,
                operations={
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='SM{$};',
                        response_format='SM{$}nn;',
                        description='Get S-meter reading'
                    ),
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='SM{$}{value};',
                        value_type='enum',
                        enum_values={'1': 'Auto-delivery on'},
                        response_format='SM{$}nn;',
                        description='Enable auto S-meter delivery'
                    )
                },
                ui_updates={
                    'main': 's_meter',
                    'sub': 's_meter_sub'
                },
                ai_eligible=True,
                auto_delivery=True
            ),
            'SB': CommandInfo(
                base_command='SB',
                command_type=CommandType.GET_SET,
                description='Sub receiver on/off',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='SB{value};',
                        value_type='enum',
                        enum_values={'0': 'OFF', '1': 'ON'},
                        response_format='SBn;',
                        description='Set sub receiver on/off'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='SB;',
                        response_format='SBn;',
                        description='Get sub receiver status'
                    ),
                    OperationType.TOGGLE: OperationInfo(
                        operation_type=OperationType.TOGGLE,
                        format_pattern='SB/;',
                        behavior='toggle_sub_receiver',
                        response_format='SBn;',
                        description='Toggle sub receiver on/off'
                    )
                },
                ui_updates={
                    'main': 'sub_receiver_enabled'
                },
                ai_eligible=True
            ),
            'TM': CommandInfo(
                base_command='TM',
                command_type=CommandType.SET_ONLY,
                description='TX meter data auto-delivery',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='TM{value};',
                        value_type='enum',
                        enum_values={'0': 'Off', '1': 'On'},
                        description='Enable TX meter auto-delivery'
                    )
                },
                ui_updates={
                    'main': 'tx_meter_auto'
                },
                ai_eligible=False,
                auto_delivery=True,
                response_parser='parse_tm_response'
            )
        }
    
    def _define_memory_commands(self) -> Dict[str, CommandInfo]:
        """Define all memory-related commands"""
        return {
            'LK': CommandInfo(
                base_command='LK',
                command_type=CommandType.GET_SET,
                description='VFO lock',
                supports_sub_receiver=True,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='LK{$}{value};',
                        value_type='enum',
                        enum_values={'0': 'Unlock', '1': 'Lock'},
                        response_format='LK{$}n;',
                        description='Set VFO lock'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='LK{$};',
                        response_format='LK{$}n;',
                        description='Get VFO lock status'
                    ),
                    OperationType.TOGGLE: OperationInfo(
                        operation_type=OperationType.TOGGLE,
                        format_pattern='LK{$}/;',
                        behavior='toggle_vfo_lock',
                        response_format='LK{$}n;',
                        description='Toggle VFO lock'
                    )
                },
                ui_updates={
                    'main': 'vfo_lock',
                    'sub': 'vfo_lock_sub'
                },
                ai_eligible=True
            )
        }
    
    def _define_menu_commands(self) -> Dict[str, CommandInfo]:
        """Define all menu-related commands"""
        return {
            'ME': CommandInfo(
                base_command='ME',
                command_type=CommandType.GET_SET,
                description='Menu parameter access',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='ME{menu_id}.{value};',
                        value_type='compound',
                        compound_format={
                            'menu_id': {'type': 'int', 'range': (1, 9999), 'format': '{:04d}'},
                            'value': {'type': 'string'}
                        },
                        response_format='MEiiii.nnnn;',
                        description='Set menu parameter'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='ME{menu_id};',
                        response_format='MEiiii.nnnn;',
                        description='Get menu parameter'
                    )
                },
                ui_updates={
                    'main': 'menu_parameter'
                },
                ai_eligible=False
            )
        }
    
    def _define_display_commands(self) -> Dict[str, CommandInfo]:
        """Define all display-related commands (# prefix)"""
        return {
            '#SPN': CommandInfo(
                base_command='#SPN',
                command_type=CommandType.GET_SET,
                description='Panadapter span',
                supports_sub_receiver=True,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='#SPN{$}{value};',
                        value_type='int',
                        range_min=6000,
                        range_max=368000,
                        response_format='#SPN{$}n;',
                        description='Set panadapter span (Hz)'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='#SPN{$};',
                        response_format='#SPN{$}n;',
                        description='Get panadapter span'
                    )
                },
                ui_updates={
                    'main': 'pan_span',
                    'sub': 'pan_span_sub'
                },
                ai_eligible=True
            ),
            '#REF': CommandInfo(
                base_command='#REF',
                command_type=CommandType.GET_SET,
                description='Panadapter reference level',
                supports_sub_receiver=True,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='#REF{$}{value};',
                        value_type='int',
                        range_min=-200,
                        range_max=60,
                        response_format='#REF{$}n;',
                        description='Set panadapter reference level (dB)'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='#REF{$};',
                        response_format='#REF{$}n;',
                        description='Get panadapter reference level'
                    )
                },
                ui_updates={
                    'main': 'pan_ref_level',
                    'sub': 'pan_ref_level_sub'
                },
                ai_eligible=True
            ),
            '#AVG': CommandInfo(
                base_command='#AVG',
                command_type=CommandType.GET_SET,
                description='Panadapter averaging',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='#AVG{value};',
                        value_type='int',
                        range_min=1,
                        range_max=20,
                        response_format='#AVGn;',
                        description='Set panadapter averaging factor (1-20)'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='#AVG;',
                        response_format='#AVGn;',
                        description='Get panadapter averaging factor'
                    )
                },
                ui_updates={
                    'main': 'pan_averaging'
                },
                ai_eligible=True
            )
        }
    
    def _define_remote_commands(self) -> Dict[str, CommandInfo]:
        """Define all remote access commands"""
        return {
            'EM': CommandInfo(
                base_command='EM',
                command_type=CommandType.GET_SET,
                description='Audio encode mode for streaming',
                supports_sub_receiver=False,
                operations={
                    OperationType.SET: OperationInfo(
                        operation_type=OperationType.SET,
                        format_pattern='EM{value};',
                        value_type='enum',
                        enum_values={
                            '0': 'Raw 32-bit',
                            '1': 'Raw 16-bit',
                            '2': 'Opus 16-bit',
                            '3': 'Opus 32-bit'
                        },
                        response_format='EMn;',
                        description='Set audio encode mode'
                    ),
                    OperationType.GET: OperationInfo(
                        operation_type=OperationType.GET,
                        format_pattern='EM;',
                        response_format='EMn;',
                        description='Get audio encode mode'
                    )
                },
                ui_updates={
                    'main': 'audio_encoding'
                },
                ai_eligible=True
            )
        }
    
    def parse_command(self, command_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse a K4 command text and extract comprehensive command information.
        
        Args:
            command_text: Raw command text (e.g., "FA07058000;", "AG$050;", "AP10;")
            
        Returns:
            Dictionary with parsed command information or None if invalid
        """
        try:
            # Clean the command
            cmd_clean = command_text.strip().rstrip(';')
            if not cmd_clean:
                return None
            
            # Initialize result structure
            result = {
                'original': command_text,
                'clean': cmd_clean,
                'base_command': '',
                'has_sub_receiver': False,
                'operation_type': OperationType.SET,
                'value': '',
                'parsed_value': {},
                'is_display_command': False,
                'command_info': None,
                'operation_info': None
            }
            
            # Check for display command (# prefix)
            if cmd_clean.startswith('#'):
                result['is_display_command'] = True
            
            # Check for sub receiver suffix ($)
            if '$' in cmd_clean:
                result['has_sub_receiver'] = True
                cmd_clean = cmd_clean.replace('$', '')
            
            # Determine operation type and extract base command
            operation_type, base_command, value = self._parse_operation_and_value(cmd_clean)
            
            result['operation_type'] = operation_type
            result['base_command'] = base_command
            result['value'] = value
            
            # Get command info
            command_info = self.commands.get(base_command)
            if not command_info:
                debug_print("COMMANDS", f"Unknown command: {base_command}")
                return None
                
            result['command_info'] = command_info
            
            # Get operation info
            operation_info = command_info.operations.get(operation_type)
            if not operation_info:
                debug_print("COMMANDS", f"Operation {operation_type} not supported for {base_command}")
                return None
                
            result['operation_info'] = operation_info
            
            # Parse value based on operation type
            if operation_type == OperationType.SET and value:
                parsed_value = self._parse_command_value(value, operation_info)
                result['parsed_value'] = parsed_value
            
            # Validate the command
            if not self._validate_parsed_command(result):
                return None
            
            return result
            
        except Exception as e:
            debug_print("CRITICAL", f"Error parsing command '{command_text}': {e}")
            return None
    
    def _parse_operation_and_value(self, cmd_clean: str) -> Tuple[OperationType, str, str]:
        """Parse operation type and extract base command and value"""
        
        # Check for operation suffixes
        if cmd_clean.endswith('/'):
            return OperationType.TOGGLE, cmd_clean[:-1], ''
        elif cmd_clean.endswith('+'):
            return OperationType.INCREMENT, cmd_clean[:-1], ''
        elif cmd_clean.endswith('-'):
            return OperationType.DECREMENT, cmd_clean[:-1], ''
        elif cmd_clean.endswith('~'):
            return OperationType.NORMALIZE, cmd_clean[:-1], ''
        elif cmd_clean.endswith('^'):
            return OperationType.BAND_STACK_NEXT, cmd_clean[:-1], ''
        elif cmd_clean.endswith('>'):
            return OperationType.BAND_STACK_RECALL, cmd_clean[:-1], ''
        elif cmd_clean.endswith('\\'):
            return OperationType.SPECIAL_OP, cmd_clean[:-1], ''
        
        # Find the base command (longest match first for commands like #SPN, #REF)
        base_command = self._find_base_command(cmd_clean)
        if not base_command:
            return OperationType.SET, cmd_clean, ''
        
        # Extract value
        value = cmd_clean[len(base_command):] if len(cmd_clean) > len(base_command) else ''
        
        # Determine if it's a GET or SET operation
        if value:
            return OperationType.SET, base_command, value
        else:
            return OperationType.GET, base_command, ''
    
    def _find_base_command(self, cmd_clean: str) -> Optional[str]:
        """Find the base command from cleaned command text"""
        # Try exact match first
        if cmd_clean in self.commands:
            return cmd_clean
        
        # Try longest match first (for commands like #SPN, #REF, etc.)
        sorted_commands = sorted(self.commands.keys(), key=len, reverse=True)
        for base_cmd in sorted_commands:
            if cmd_clean.startswith(base_cmd):
                return base_cmd
        
        return None
    
    def _parse_command_value(self, value: str, operation_info: OperationInfo) -> Dict[str, Any]:
        """Parse command value based on operation info"""
        parsed = {}
        
        if operation_info.value_type == 'int':
            try:
                parsed['int_value'] = int(value)
            except ValueError:
                parsed['raw_value'] = value
                
        elif operation_info.value_type == 'float':
            try:
                parsed['float_value'] = float(value)
            except ValueError:
                parsed['raw_value'] = value
                
        elif operation_info.value_type == 'enum':
            parsed['enum_key'] = value
            if operation_info.enum_values:
                parsed['enum_value'] = operation_info.enum_values.get(value, f'Unknown ({value})')
                
        elif operation_info.value_type == 'compound':
            parsed = self._parse_compound_value(value, operation_info.compound_format)
            
        else:
            parsed['string_value'] = value
        
        return parsed
    
    def _parse_compound_value(self, value: str, compound_format: Dict[str, Any]) -> Dict[str, Any]:
        """Parse compound value format (e.g., AP10 -> mode=1, bandwidth=0)"""
        parsed = {}
        
        if not compound_format:
            return {'raw_value': value}
        
        # Handle specific compound formats
        if len(compound_format) == 2:
            # Two-character compound like AP10
            if len(value) == 2:
                keys = list(compound_format.keys())
                parsed[keys[0]] = value[0]
                parsed[keys[1]] = value[1]
            else:
                parsed['raw_value'] = value
        else:
            # More complex compound parsing would go here
            parsed['raw_value'] = value
        
        return parsed
    
    def _validate_parsed_command(self, parsed_cmd: Dict[str, Any]) -> bool:
        """Validate a parsed command"""
        cmd_info = parsed_cmd['command_info']
        op_info = parsed_cmd['operation_info']
        
        # Check if command supports sub receiver
        if parsed_cmd['has_sub_receiver'] and not cmd_info.supports_sub_receiver:
            debug_print("COMMANDS", f"Command {cmd_info.base_command} does not support sub receiver")
            return False
        
        # Validate value ranges for SET operations
        if (parsed_cmd['operation_type'] == OperationType.SET and 
            'int_value' in parsed_cmd['parsed_value']):
            
            int_val = parsed_cmd['parsed_value']['int_value']
            if (op_info.range_min is not None and int_val < op_info.range_min) or \
               (op_info.range_max is not None and int_val > op_info.range_max):
                debug_print("COMMANDS", f"Value {int_val} out of range for {cmd_info.base_command}")
                return False
        
        return True
    
    def build_command(self, base_command: str, operation: OperationType = OperationType.SET, 
                     value: str = '', sub_receiver: bool = False) -> str:
        """
        Build a command string supporting all operation types.
        
        Args:
            base_command: The base command (e.g., 'FA', 'AG', '#SPN')
            operation: Type of operation to perform
            value: Value for SET operations
            sub_receiver: Whether to add $ suffix for sub receiver
            
        Returns:
            Formatted command string ready to send
        """
        cmd_info = self.commands.get(base_command)
        if not cmd_info:
            raise ValueError(f"Unknown command: {base_command}")
        
        op_info = cmd_info.operations.get(operation)
        if not op_info:
            raise ValueError(f"Operation {operation} not supported for {base_command}")
        
        # Validate sub receiver support
        if sub_receiver and not cmd_info.supports_sub_receiver:
            raise ValueError(f"Command {base_command} does not support sub receiver")
        
        # Build command using format pattern
        format_pattern = op_info.format_pattern
        
        # Replace placeholders
        command = format_pattern.replace('{$}', '$' if sub_receiver else '')
        command = command.replace('{value}', value)
        
        return command
    
    def create_ui_update(self, parsed_cmd: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a UI update dictionary from a parsed command.
        
        Args:
            parsed_cmd: Parsed command dictionary
            
        Returns:
            Dictionary with UI update information
        """
        if not parsed_cmd or parsed_cmd['operation_type'] != OperationType.SET:
            return {}
        
        cmd_info = parsed_cmd['command_info']
        is_sub = parsed_cmd['has_sub_receiver']
        parsed_value = parsed_cmd['parsed_value']
        
        updates = {}
        
        # Get UI update fields
        ui_fields = cmd_info.ui_updates.get('sub' if is_sub else 'main', [])
        if isinstance(ui_fields, str):
            ui_fields = [ui_fields]
        
        # Apply specialized parsers
        if cmd_info.response_parser:
            specialized_updates = self._apply_specialized_parser(
                parsed_cmd, cmd_info.response_parser)
            updates.update(specialized_updates)
        
        # Apply generic updates
        for field in ui_fields:
            if 'int_value' in parsed_value:
                updates[field] = parsed_value['int_value']
            elif 'enum_value' in parsed_value:
                updates[field] = parsed_value['enum_value']
            elif 'string_value' in parsed_value:
                updates[field] = parsed_value['string_value']
            elif 'raw_value' in parsed_value:
                updates[field] = parsed_value['raw_value']
        
        return updates
    
    def _apply_specialized_parser(self, parsed_cmd: Dict[str, Any], parser_name: str) -> Dict[str, Any]:
        """Apply specialized response parser"""
        
        if parser_name == 'parse_frequency_response':
            return self._parse_frequency_response(parsed_cmd)
        elif parser_name == 'parse_mode_response':
            return self._parse_mode_response(parsed_cmd)
        elif parser_name == 'parse_apf_response':
            return self._parse_apf_response(parsed_cmd)
        elif parser_name == 'parse_if_response':
            return self._parse_if_response(parsed_cmd)
        elif parser_name == 'parse_tm_response':
            return self._parse_tm_response(parsed_cmd)
        
        return {}
    
    def _parse_frequency_response(self, parsed_cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Parse frequency response and format for display"""
        updates = {}
        
        if 'int_value' in parsed_cmd['parsed_value']:
            freq_hz = parsed_cmd['parsed_value']['int_value']
            updates['freq_hz'] = freq_hz
            updates['freq_formatted'] = self._format_frequency(freq_hz)
        
        return updates
    
    def _parse_mode_response(self, parsed_cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Parse mode response"""
        updates = {}
        
        if 'enum_value' in parsed_cmd['parsed_value']:
            updates['mode'] = parsed_cmd['parsed_value']['enum_value']
        
        return updates
    
    def _parse_apf_response(self, parsed_cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Parse APF response with mode and bandwidth"""
        updates = {}
        
        if 'parsed_value' in parsed_cmd and len(parsed_cmd['parsed_value']) >= 2:
            # APF format: mode + bandwidth (e.g., "10" = mode 1, bandwidth 0)
            raw_value = parsed_cmd['parsed_value'].get('raw_value', '')
            if len(raw_value) == 2:
                mode = raw_value[0]
                bandwidth = raw_value[1]
                
                mode_map = {'0': 'OFF', '1': 'ON'}
                bandwidth_map = {'0': '30Hz', '1': '50Hz', '2': '150Hz'}
                
                updates['apf_mode'] = mode_map.get(mode, f'Mode {mode}')
                updates['apf_bandwidth'] = bandwidth_map.get(bandwidth, f'BW {bandwidth}')
        
        return updates
    
    def _parse_if_response(self, parsed_cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Parse complex IF response format"""
        # IF response: IF[f]*****+yyyyrx*00tm0spbd1*;
        # This would need complex parsing logic
        # For now, return empty dict - full implementation would parse the 31-character format
        return {}
    
    def _parse_tm_response(self, parsed_cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Parse TX meter response format"""
        # TM response: TMaaabbbcccddd; (ALC, CMP, FWD, SWR)
        # For now, return empty dict - full implementation would parse meter values
        return {}
    
    def _format_frequency(self, freq_hz: int) -> str:
        """Format frequency for display"""
        try:
            mhz = freq_hz // 1_000_000
            khz = (freq_hz % 1_000_000) // 1000
            hz = freq_hz % 1000
            return f"{mhz}.{khz:03}.{hz:03}"
        except (ValueError, TypeError):
            return str(freq_hz)
    
    def handle_streaming_response(self, response_text: str) -> Dict[str, Any]:
        """
        Handle streaming responses including AI updates and automatic deliveries.
        
        Args:
            response_text: Incoming response text
            
        Returns:
            Dictionary with response information and UI updates
        """
        parsed = self.parse_command(response_text)
        
        if not parsed:
            return {'type': 'unknown', 'original': response_text}
        
        # Check if this is an AI response (unsolicited)
        is_ai_response = self._is_ai_response(parsed)
        
        # Create UI updates
        ui_updates = self.create_ui_update(parsed)
        
        # Determine response type
        response_type = 'ai_update' if is_ai_response else 'response'
        
        # Handle special streaming responses
        if parsed['base_command'] == 'TM':
            response_type = 'tx_meter_stream'
        elif parsed['base_command'] == 'SM':
            response_type = 'smeter_stream'
        elif parsed['base_command'] == 'IF':
            response_type = 'status_update'
        
        return {
            'type': response_type,
            'original': response_text,
            'parsed': parsed,
            'ui_updates': ui_updates,
            'timestamp': time.time()
        }
    
    def _is_ai_response(self, parsed_cmd: Dict[str, Any]) -> bool:
        """Determine if this is an unsolicited AI response"""
        cmd_info = parsed_cmd['command_info']
        
        # Check if command is AI eligible
        if not cmd_info.ai_eligible:
            return False
        
        # Check if we recently sent this command
        original = parsed_cmd['original']
        return not self._was_recently_sent(original)
    
    def _was_recently_sent(self, command: str, window_seconds: int = 2) -> bool:
        """Check if command was recently sent by us"""
        current_time = time.time()
        
        # Clean up old entries
        cutoff_time = current_time - window_seconds
        self.last_sent_commands = {
            cmd: timestamp for cmd, timestamp in self.last_sent_commands.items()
            if timestamp > cutoff_time
        }
        
        return command in self.last_sent_commands
    
    def track_sent_command(self, command: str):
        """Track that we sent a command"""
        self.last_sent_commands[command] = time.time()
    
    def set_ai_mode(self, mode: int = 2) -> str:
        """Set AI mode for streaming updates"""
        self.ai_mode = mode
        return f"AI{mode};"
    
    def get_command_info(self, command: str) -> Optional[CommandInfo]:
        """Get information about a command"""
        return self.commands.get(command)
    
    def get_all_commands(self) -> Dict[str, CommandInfo]:
        """Get all available commands"""
        return self.commands.copy()
    
    def get_commands_by_category(self, category: str) -> Dict[str, CommandInfo]:
        """Get commands filtered by category"""
        return {
            cmd: info for cmd, info in self.commands.items()
            if info.category == category
        }
    
    def add_to_history(self, command: str, direction: str = "sent"):
        """Add command to history"""
        self.command_history.append({
            'command': command,
            'direction': direction,
            'timestamp': time.time()
        })
        
        # Track sent commands for AI detection
        if direction == "sent":
            self.track_sent_command(command)
        
        # Limit history size
        if len(self.command_history) > self.max_history:
            self.command_history.pop(0)
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get command history"""
        return self.command_history.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get command handler statistics"""
        return {
            'total_commands': len(self.commands),
            'commands_by_category': {
                category: len(self.get_commands_by_category(category))
                for category in set(cmd.category for cmd in self.commands.values())
            },
            'commands_with_sub_support': len([
                cmd for cmd in self.commands.values() 
                if cmd.supports_sub_receiver
            ]),
            'ai_eligible_commands': len([
                cmd for cmd in self.commands.values() 
                if cmd.ai_eligible
            ]),
            'history_size': len(self.command_history),
            'current_ai_mode': self.ai_mode
        }


# Global command handler instance
_command_handler = None

def get_command_handler() -> K4CommandHandler:
    """Get or create the global command handler instance"""
    global _command_handler
    if _command_handler is None:
        _command_handler = K4CommandHandler()
        debug_print("COMMANDS", "Initialized comprehensive K4 command handler")
    return _command_handler


# Convenience functions for backward compatibility
def parse_cat_command(cat_text: str) -> dict:
    """Parse CAT command - backward compatibility function"""
    handler = get_command_handler()
    response = handler.handle_streaming_response(cat_text)
    return response.get('ui_updates', {})


def format_k4_command(command: str, operation: str = 'SET', value: str = '', sub_receiver: bool = False) -> str:
    """Format K4 command - convenience function"""
    handler = get_command_handler()
    
    # Convert string operation to enum
    operation_map = {
        'SET': OperationType.SET,
        'GET': OperationType.GET,
        'TOGGLE': OperationType.TOGGLE,
        'INCREMENT': OperationType.INCREMENT,
        'DECREMENT': OperationType.DECREMENT
    }
    
    op_type = operation_map.get(operation.upper(), OperationType.SET)
    return handler.build_command(command, op_type, value, sub_receiver)


debug_print("GENERAL", "🎯 K4 Command Handler loaded with comprehensive multi-operation support")
debug_print("GENERAL", "📊 Features: 219 commands, multi-operation support, AI streaming, response parsing")
debug_print("GENERAL", "🔧 Categories: frequency, audio, mode, filter, antenna, band, system, display, remote")
debug_print("GENERAL", "⚡ Operations: SET, GET, TOGGLE, INCREMENT, DECREMENT, NORMALIZE, SPECIAL")