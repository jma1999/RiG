import React, { useState, useEffect } from 'react';
import { Box, MapPin, Building2, Activity, Search, Filter } from 'lucide-react';
import { API_BASE } from "@/lib/env";

const AssetsView = ({ assets, spaces, onNodeClick }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [selectedItem, setSelectedItem] = useState(null);

  const filteredAssets = assets.filter(a => {
    const matchesSearch = !searchQuery || 
      a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filterType === 'all' || a.type.toLowerCase().includes(filterType.toLowerCase());
    return matchesSearch && matchesFilter;
  });

  const filteredSpaces = spaces.filter(s => {
    const matchesSearch = !searchQuery || 
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  const handleItemClick = (item) => {
    setSelectedItem(item);
    if (onNodeClick) {
      onNodeClick({
        id: item.id,
        label: item.name,
        type: item.type,
        ...item
      });
    }
  };

  const getTypeIcon = (type) => {
    if (type.includes('Space') || type === 'Space') return MapPin;
    if (type.includes('AHU') || type.includes('Equipment')) return Activity;
    return Box;
  };

  const getTypeColor = (type) => {
    if (type.includes('Space') || type === 'Space') return 'text-nexus-accent';
    if (type.includes('AHU')) return 'text-nexus-success';
    if (type.includes('VAV')) return 'text-nexus-warning';
    return 'text-slate-400';
  };

  return (
    <div className="h-full w-full bg-nexus-800 rounded-lg border border-nexus-600 p-6 overflow-y-auto">
      
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-white tracking-wide flex items-center gap-3">
            <Building2 className="text-nexus-accent" />
            ASSETS & SPACES
          </h2>
          <p className="text-sm text-slate-400 mt-1 font-mono">
             SEMANTIC INVENTORY FROM GRAPHDB (IFC-LD + BRICK + 223P)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="bg-nexus-900/80 border border-nexus-700 px-3 py-1.5 rounded-lg">
            <span className="text-xs font-mono text-nexus-accent">{assets.length} Assets</span>
          </div>
          <div className="bg-nexus-900/80 border border-nexus-700 px-3 py-1.5 rounded-lg">
            <span className="text-xs font-mono text-nexus-accent">{spaces.length} Spaces</span>
          </div>
        </div>
      </div>

      {/* Search and Filter */}
      <div className="flex gap-3 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
          <input
            type="text"
            placeholder="Search assets or spaces..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-nexus-900 text-white placeholder:text-slate-500 border border-nexus-700 rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-nexus-accent/50 text-sm"
          />
        </div>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="bg-nexus-900 text-white border border-nexus-700 rounded-lg px-4 py-2 focus:outline-none focus:border-nexus-accent/50 text-sm"
        >
          <option value="all">All Types</option>
          <option value="equipment">Equipment</option>
          <option value="ahu">AHU</option>
          <option value="vav">VAV</option>
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Assets Section */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Box className="text-nexus-accent" size={18} />
            <h3 className="text-sm font-mono text-nexus-accent uppercase tracking-wider">
              Equipment & Assets ({filteredAssets.length})
            </h3>
          </div>
          
          {filteredAssets.length === 0 ? (
            <div className="p-8 border border-dashed border-nexus-600 rounded-lg text-center text-slate-500">
              <Box size={32} className="mx-auto mb-2 opacity-20" />
              <p className="text-sm">No assets found</p>
              <p className="text-xs mt-1 text-slate-600">Check GraphDB connection</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {filteredAssets.map((asset) => {
                const Icon = getTypeIcon(asset.type);
                return (
                  <div
                    key={asset.id}
                    onClick={() => handleItemClick(asset)}
                    className={`p-4 rounded-lg border transition-all cursor-pointer ${
                      selectedItem?.id === asset.id
                        ? 'bg-nexus-900 border-nexus-accent'
                        : 'bg-nexus-900/50 border-nexus-700 hover:border-nexus-accent/50 hover:bg-nexus-900'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3 flex-1">
                        <div className={`p-2 rounded-lg bg-nexus-800 ${getTypeColor(asset.type)}`}>
                          <Icon size={18} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-white truncate">{asset.name}</p>
                          <p className="text-xs text-slate-400 mt-1">{asset.type}</p>
                          <p className="text-xs text-slate-500 font-mono mt-1 truncate">{asset.id}</p>
                        </div>
                      </div>
                      <div className={`w-2 h-2 rounded-full ${
                        asset.status === 'warning' ? 'bg-nexus-warning' :
                        asset.status === 'critical' ? 'bg-nexus-danger' :
                        'bg-nexus-success'
                      }`}></div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Spaces Section */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <MapPin className="text-nexus-accent" size={18} />
            <h3 className="text-sm font-mono text-nexus-accent uppercase tracking-wider">
              Spaces ({filteredSpaces.length})
            </h3>
          </div>
          
          {filteredSpaces.length === 0 ? (
            <div className="p-8 border border-dashed border-nexus-600 rounded-lg text-center text-slate-500">
              <MapPin size={32} className="mx-auto mb-2 opacity-20" />
              <p className="text-sm">No spaces found</p>
              <p className="text-xs mt-1 text-slate-600">Check GraphDB connection</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {filteredSpaces.map((space) => (
                <div
                  key={space.id}
                  onClick={() => handleItemClick(space)}
                  className={`p-4 rounded-lg border transition-all cursor-pointer ${
                    selectedItem?.id === space.id
                      ? 'bg-nexus-900 border-nexus-accent'
                      : 'bg-nexus-900/50 border-nexus-700 hover:border-nexus-accent/50 hover:bg-nexus-900'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-nexus-800 text-nexus-accent">
                      <MapPin size={18} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white truncate">{space.name}</p>
                      <p className="text-xs text-slate-400 mt-1">IFC Space</p>
                      <p className="text-xs text-slate-500 font-mono mt-1 truncate">{space.id}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>

      {/* Selected Item Details */}
      {selectedItem && (
        <div className="mt-6 p-4 bg-nexus-900/50 border border-nexus-700 rounded-lg">
          <h4 className="text-sm font-bold text-white mb-2">Selected: {selectedItem.name}</h4>
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <span className="text-slate-400">Type:</span>
              <span className="text-white ml-2">{selectedItem.type}</span>
            </div>
            <div>
              <span className="text-slate-400">ID:</span>
              <span className="text-white ml-2 font-mono truncate">{selectedItem.id}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AssetsView;



