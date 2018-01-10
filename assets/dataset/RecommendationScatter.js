import React from 'react';


class RecommendationScatter extends React.Component {

    constructor(props) {
        super(props);

        var exp_type_choices = (['--']).concat(Object.keys(this.props.data));

        this.state = {
            exp_type: '--',
            exp_type_choices: exp_type_choices,
        };
    }

    drawPlotly(){
        var x = [], y = [];

        if (this.state.exp_type != '--') {
            var _data = this.props.data[this.state.exp_type];
            for(var i = 0; i < _data.length; i++){
                // genes.push(this.props.data[i][0]);
                x.push(_data[i][0]);
                y.push(_data[i][1]);
            }
        }

        var plot_data = [{
            x: x,
            y: y,
            mode: 'markers',
            type: 'scatter',
            // text: genes,
        }];

        var layout = {
            xaxis: {
                // type: 'log',
                autorange: true,
            },
            yaxis: {
                // type: 'log',
                autorange: true,
            },
        };

        Plotly.newPlot('rec_scatter_plot', plot_data, layout);
    }

    componentDidMount(){
        this.drawPlotly();

        for (let i in this.state.exp_type_choices) {
            $(this.refs.exp_type_select).append(
                '<option val="' + i + '">' + this.state.exp_type_choices[i] + '</option>');
        }
    }

    componentWillUnmount(){
        $(this.refs.gene_scatter_plot).clear();
    }

    update_exp_type(event){
        this.setState({
            exp_type: event.target.value,
        }, this.drawPlotly);
    }

    render(){
        return <div>
            <select ref='exp_type_select'
                onChange={this.update_exp_type.bind(this)}
                value={this.state.exp_type}>
            </select>
            <div ref='rec_scatter_plot' id='rec_scatter_plot'></div>
        </div>;
    }
}

RecommendationScatter.propTypes = {
    data: React.PropTypes.object.isRequired,
};

export default RecommendationScatter;